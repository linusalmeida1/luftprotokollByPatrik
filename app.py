#!/usr/bin/env python3
"""Single-user, loopback-only pilot. Start: python app.py --open."""
import argparse
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import time
from urllib.parse import urlparse, parse_qs
import uuid
import webbrowser
from domain import normalize_row, calculate
from exporter import workbook_bytes
import ai

ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('LUFT_DATA_DIR',str(ROOT/'data'))).resolve()
TOKEN=secrets.token_urlsafe(32)
JOBS={}
JOB_LOCK=threading.Lock()
MAX_FILE=20*1024*1024

def connection():
    DATA.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(DATA/'luftprotokoll.sqlite',timeout=30)
    con.execute('CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
    con.execute('CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, project_id TEXT, created REAL, data TEXT)')
    return con

def read_project(pid):
    with connection() as con: item=con.execute('SELECT data FROM projects WHERE id=?',(pid,)).fetchone()
    if not item: raise ValueError('Uppdraget finns inte.')
    return json.loads(item[0])

def mutate(pid, fn, revision=None):
    with connection() as con:
        con.execute('BEGIN IMMEDIATE')
        item=con.execute('SELECT data FROM projects WHERE id=?',(pid,)).fetchone()
        if not item: raise ValueError('Uppdraget finns inte.')
        old=json.loads(item[0])
        if revision is not None and revision != old['revision']:
            raise ValueError('Uppdraget har ändrats. Ladda om sidan innan du sparar.')
        fn(old)
        old['revision']+=1
        old['updated']=time.time()
        con.execute('INSERT INTO history(project_id,created,data) VALUES(?,?,?)',(pid,time.time(),item[0]))
        con.execute('UPDATE projects SET data=? WHERE id=?',(json.dumps(old,ensure_ascii=False),pid))
    return old

def new_project(name):
    name=str(name).strip()[:150]
    if not name: raise ValueError('Ange ett namn på uppdraget.')
    project={'id':uuid.uuid4().hex,'name':name,'technician':'','date':'','rows':[], 'files':[], 'revision':1,'updated':time.time()}
    with connection() as con: con.execute('INSERT INTO projects VALUES(?,?)',(project['id'],json.dumps(project)))
    return project

def project_view(project):
    copy=json.loads(json.dumps(project))
    for row in copy['rows']: row['calculation']=calculate(row)
    return copy

def validate_file(name, encoded):
    if len(encoded)>MAX_FILE*1.4: raise ValueError('Filen är för stor. Högst 20 MB per fil.')
    try: raw=base64.b64decode(encoded,validate=True)
    except ValueError: raise ValueError('Filen kunde inte läsas.') from None
    if not raw or len(raw)>MAX_FILE: raise ValueError('Filen är tom eller större än 20 MB.')
    if raw.startswith(b'%PDF-'): mime='application/pdf';ext='.pdf'
    elif raw.startswith(b'\x89PNG\r\n\x1a\n'): mime='image/png';ext='.png'
    elif raw.startswith(b'\xff\xd8\xff'): mime='image/jpeg';ext='.jpg'
    else: raise ValueError('Välj PDF, PNG eller JPEG. HEIC behöver först konverteras till JPEG.')
    safe=Path(str(name).replace('\\','/')).name[:180]
    if not safe: safe='ritning'+ext
    return raw,mime,safe

def run_job(job_id,pid,fid):
    try:
        project=read_project(pid)
        file=next(f for f in project['files'] if f['id']==fid)
        candidates=ai.extract(DATA/'files'/fid,file['mime'],file['name'])
        rows=[normalize_row({**r,'id':uuid.uuid4().hex,'source_file':fid,'reviewed':False,'excluded':False}) for r in candidates]
        def save(p):
            if any(f.get('analyzed') for f in p['files'] if f['id']==fid): raise ValueError('Filen har redan analyserats.')
            p['rows'].extend(rows)
            for f in p['files']:
                if f['id']==fid: f['analyzed']=True
        mutate(pid,save)
        with JOB_LOCK: JOBS[job_id].update(status='done',count=len(rows))
    except Exception as exc:
        message=str(exc) if isinstance(exc,ValueError) else 'Avläsningen misslyckades. Inga mätposter importerades.'
        with JOB_LOCK: JOBS[job_id].update(status='failed',error=message)

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass  # Avoid filenames or API data in terminal logs.

    def send(self,status,data,ctype='application/json; charset=utf-8',download=None):
        if isinstance(data,(dict,list)): data=json.dumps(data,ensure_ascii=False).encode()
        elif isinstance(data,str): data=data.encode()
        self.send_response(status)
        self.send_header('Content-Type',ctype)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-src 'self'; object-src 'self'; base-uri 'none'; frame-ancestors 'none'")
        if download: self.send_header('Content-Disposition',f'attachment; filename="{download}"')
        self.end_headers()
        self.wfile.write(data)

    def trusted(self,write=False):
        expected=f'127.0.0.1:{self.server.server_port}'
        if self.headers.get('Host')!=expected: raise ValueError('Fel värdadress. Använd programmets lokala länk.')
        origin=self.headers.get('Origin')
        if origin and origin!='http://'+expected: raise ValueError('Begäran från annan webbplats nekades.')
        if write and not secrets.compare_digest(self.headers.get('X-Luft-Token',''),TOKEN):
            raise ValueError('Sessionen har ändrats. Ladda om sidan.')

    def do_GET(self):
        try:
            self.trusted()
            url=urlparse(self.path); path=url.path; q=parse_qs(url.query)
            if path=='/':
                page=(ROOT/'static/index.html').read_text().replace('TOKEN_PLACEHOLDER',TOKEN)
                return self.send(200,page,'text/html; charset=utf-8')
            if path in ('/app.js','/style.css'):
                return self.send(200,(ROOT/'static'/path[1:]).read_bytes(),'text/javascript' if path.endswith('.js') else 'text/css')
            if path=='/api/projects':
                with connection() as con: items=[json.loads(r[0]) for r in con.execute('SELECT data FROM projects')]
                return self.send(200,{'projects':[{'id':p['id'],'name':p['name'],'updated':p['updated'],'count':len(p['rows'])} for p in sorted(items,key=lambda p:-p['updated'])],
                                     'ai_ready':bool(os.environ.get('OPENAI_API_KEY') and os.environ.get('LUFT_AI_MODEL'))})
            parts=path.strip('/').split('/')
            if len(parts)==3 and parts[:2]==['api','projects']:
                return self.send(200,project_view(read_project(parts[2])))
            if len(parts)==3 and parts[:2]==['api','jobs']:
                with JOB_LOCK: job=dict(JOBS.get(parts[2],{'status':'failed','error':'Jobbet finns inte. Ladda om uppdraget.'}))
                return self.send(200,job)
            if len(parts)==4 and parts[:2]==['api','projects']:
                project=read_project(parts[2])
                if parts[3]=='export':
                    result=workbook_bytes(project,draft=q.get('draft')==['1'])
                    return self.send(200,result,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','Luftprotokoll.xlsx')
                if parts[3]=='backup':
                    return self.send(200,project,'application/json; charset=utf-8','uppdrag.json')
            if len(parts)==5 and parts[:2]==['api','projects'] and parts[3]=='files':
                project=read_project(parts[2]);file=next((f for f in project['files'] if f['id']==parts[4]),None)
                if not file: raise ValueError('Filen finns inte i uppdraget.')
                return self.send(200,(DATA/'files'/file['id']).read_bytes(),file['mime'])
            return self.send(404,{'error':'Sidan finns inte.'})
        except ValueError as exc: self.send(400,{'error':str(exc)})
        except (BrokenPipeError,ConnectionResetError): pass
        except Exception: self.send(500,{'error':'Ett lokalt fel inträffade. Uppgifterna är sparade om senaste sparningen lyckades.'})

    def do_POST(self):
        try:
            self.trusted(write=True)
            if self.headers.get('Content-Type','').split(';')[0]!='application/json': raise ValueError('JSON krävs.')
            length=int(self.headers.get('Content-Length','0'))
            if length<1 or length>MAX_FILE*1.4+20000: raise ValueError('Begäran är för stor eller tom.')
            body=json.loads(self.rfile.read(length))
            path=urlparse(self.path).path;parts=path.strip('/').split('/')
            if path=='/api/projects': return self.send(201,project_view(new_project(body.get('name',''))))
            if len(parts)!=4 or parts[:2]!=['api','projects']: return self.send(404,{'error':'Okänd åtgärd.'})
            pid,action=parts[2:]
            if action=='save':
                if not isinstance(body.get('rows'),list) or len(body['rows'])>5000: raise ValueError('Ogiltig mätlista.')
                rows=[normalize_row(r) for r in body['rows']]
                if len({r['id'] for r in rows})!=len(rows): raise ValueError('Dubbla mätpost-ID.')
                def update(p):
                    file_ids={f['id'] for f in p['files']}
                    if any(r['source_file'] and r['source_file'] not in file_ids for r in rows): raise ValueError('En källfil saknas.')
                    # Editing validated values invalidates old approval unless deliberately approved again in editor.
                    p['rows']=rows
                    for key in ('name','technician','date'):p[key]=str(body.get(key,p[key]))[:150]
                    if not p['name'].strip():raise ValueError('Uppdragsnamn saknas.')
                return self.send(200,project_view(mutate(pid,update,body.get('revision',-1))))
            if action=='upload':
                raw,mime,name=validate_file(body.get('name',''),body.get('data',''))
                read_project(pid)
                digest=hashlib.sha256(raw).hexdigest();fid=uuid.uuid4().hex
                (DATA/'files').mkdir(exist_ok=True)
                (DATA/'files'/fid).write_bytes(raw)
                def update(p):
                    if any(f['sha256']==digest for f in p['files']): raise ValueError('Filen finns redan i uppdraget.')
                    p['files'].append({'id':fid,'name':name,'mime':mime,'sha256':digest,'analyzed':False})
                try: project=mutate(pid,update)
                except Exception:
                    (DATA/'files'/fid).unlink(missing_ok=True);raise
                return self.send(200,project_view(project))
            if action=='analyze':
                if body.get('consent') is not True: raise ValueError('Bekräfta extern behandling först.')
                if not os.environ.get('OPENAI_API_KEY') or not os.environ.get('LUFT_AI_MODEL'): raise ValueError('AI är inte konfigurerad på datorn.')
                p=read_project(pid);fid=body.get('file_id')
                f=next((f for f in p['files'] if f['id']==fid),None)
                if not f or f.get('analyzed'): raise ValueError('Filen saknas eller har redan analyserats.')
                with JOB_LOCK:
                    if any(j['status']=='running' for j in JOBS.values()): raise ValueError('En avläsning pågår. Vänta tills den är klar.')
                    jid=uuid.uuid4().hex;JOBS[jid]={'status':'running','project_id':pid,'file_id':fid}
                threading.Thread(target=run_job,args=(jid,pid,fid),daemon=True).start()
                return self.send(202,{'job_id':jid})
            return self.send(404,{'error':'Okänd åtgärd.'})
        except (ValueError,TypeError,KeyError) as exc: self.send(400,{'error':str(exc)})
        except (BrokenPipeError,ConnectionResetError): pass
        except Exception: self.send(500,{'error':'Åtgärden misslyckades. Inga osparade ändringar har bekräftats.'})

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--open',action='store_true')
    args=parser.parse_args()
    connection().close()
    try: server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    except OSError as exc: raise SystemExit(f'Kunde inte starta lokal server: {exc}. Om porten är upptagen, välj --port 8766.')
    server.daemon_threads=True
    url=f'http://127.0.0.1:{server.server_port}'
    print(f'Luftprotokoll startat: {url}\nAvsluta med Ctrl+C. Data: {DATA}')
    if args.open: threading.Timer(0.5,lambda:webbrowser.open(url)).start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
