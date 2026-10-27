# Luftprotokoll – lokal pilot

Programmet har uppladdning av PDF/JPEG/PNG, lokal lagring, redigerbar mätlista,
källvisning, granskning, enhetsomvandling och export till en fast Excel-layout för
stående A4. Det startas som ett lokalt program och visas i webbläsaren.

## Kom igång på Windows

1. Packa upp hela mappen till exempelvis `C:\Luftprotokoll`. Kör inte direkt från zip-filen.
2. Installera Python 3.11 eller senare från https://www.python.org/downloads/windows/ med Python Launcher.
3. Öppna PowerShell i programmappen och kör:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Installera.ps1
```

Kommandot tillåter installationsskriptet i just denna process; det ändrar inte datorns permanenta skriptpolicy.
Installationen hämtar det låsta Excel-biblioteket och kör kontrolltester.

4. Dubbelklicka på `Starta.cmd`. Webbläsaren öppnar `http://127.0.0.1:8765`.
5. Prova **Exempelvärden**. Granska posterna, godkänn dem och exportera.
6. Skapa ett riktigt uppdrag och lägg till ritningar.

Låt terminalfönstret vara öppet medan programmet används. Stäng programmet med Ctrl+C.
Ingen Excel-installation krävs för att skapa filen. Prova utskrift i kollegans Excel innan skarp användning.

## AI-avläsning – valbar och ännu inte provad mot ett livekonto

Programmet fungerar manuellt utan AI. Extern avläsning behöver ett OpenAI API-konto,
API-nyckel, en modell som stöder bilder/PDF och strukturerade svar samt tillåtelse att
skicka ritningar till tjänsten. En ChatGPT-prenumeration är inte inställningen som programmet använder.

Ställ in miljövariabler i samma PowerShell-fönster som används för att starta programmet.
Nyckeln ska inte skrivas i källkoden eller checkas in i Git. Följande läser den dolt:

```powershell
$luftKey = Read-Host 'OpenAI API-nyckel' -AsSecureString
$env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new('', $luftKey).Password
$env:LUFT_AI_MODEL = Read-Host 'Modell-ID som är tillgängligt på ditt API-konto'
.\Starta.ps1
```

Om datorns policy blockerar sista kommandot, kör `cmd /c Starta.cmd` i samma fönster.
Variablerna gäller för detta fönster och de program som startas därifrån. De lagras inte av appen.
Välj **Läs av med AI** vid en fil och bekräfta extern behandling. Kostnad tillkommer på API-kontot.
Filen skickas bara efter detta val. Appen använder `store: false`; tjänstens egna regler för
databehandling och loggning gäller ändå. Läs dem för ert avtal innan känsliga ritningar skickas.

Avläsningen skickar hela filen och kan ta flera minuter. För stora ritningar rekommenderas
tydliga skanningar eller separata närbilder. Piloten har inte automatisk uppdelning i högupplösta
utsnitt och kan därför missa små don eller svår handskrift. En tom AI-lista betyder inte att ritningen saknar mätningar.
Kontrollera originalet. Modellspecifika begränsningar behöver provas med ert konto.

## Arbetsflöde

- Skapa ett uppdrag. Uppdragsnamn, mättekniker och mätdatum hamnar i sidhuvudet.
- Lägg till flera ritningar. Dubbletter inom samma uppdrag blockeras.
- Läs av en fil i taget med AI, eller lägg in mätningar själv.
- Öppna en mätpost. Originalet visas bredvid formuläret. För PDF kan du ange sida.
- Bekräfta enheter och om värdet avser ett don eller en hel grupp.
- Saknat värde lämnas tomt. Ett verkligt nollflöde skrivs som `0` och kommer med i exporten.
- Bocka i granskning och spara. Ändrade värden kräver ny granskning i formuläret.
- Uteslut kandidater som inte ska ingå. Slutlig export blockeras om någon kvarvarande post saknar
  rum, mätvärde, mätenhet, omfattning eller granskning. Enhet behövs även för angivet projekterat värde.
- Saknat projekterat flöde tillåts: uppmätt flöde visas men procentsiffran lämnas tom.
- Utkast kan exporteras innan allt är granskat och märks tydligt UTKAST.

## Beräkningar och utskrift

Omräkning: `m³/h ÷ 3,6 = l/s`. Andel av projekterat: `uppmätt l/s ÷ projekterat l/s`.
Excel visar andelen i procent. 100 % betyder samma flöde. Inga godkänt/underkänt-gränser antas.
Originalvärden och enheter finns kvar i fliken Mätunderlag. Protokollflikarna är inställda
för stående A4, en sida per flik. Välj protokollflikarna, inte Mätunderlag, vid utskrift.
Procentkolumnerna är Excel-formler och räknas när arbetsboken öppnas.

Ändra och spara helst mätningarna i appen och exportera igen. Exceländringar synkroniseras
inte tillbaka till appen, och ändringar i fliken Mätunderlag räknar inte om protokollens flöden.

Ingen automatisk fördelning eller summering av don görs i piloten. Ange en verifierad gruppsumma
som en egen mätpost när projekteringen avser gruppen. Programmet kan inte själv bevisa att rätt don har hittats.

## Lagring och säkerhetskopiering

Uppdrag och versionshistorik finns i `data/luftprotokoll.sqlite`; originalen i `data/files/`.
För säkerhetskopia: stoppa programmet och kopiera hela `data/`-mappen till er vanliga backup.
Knappen **Exportera uppdragsdata** ger JSON med värden och filreferenser, inte originalfilerna.
JSON-import/återställningsknapp ingår inte i piloten. Säkerhetskopian av `data/` kan återställas
genom att kopiera tillbaka hela mappen när programmet är stoppat.

Ingen användarinloggning eller databaskryptering ingår. Appen lyssnar bara på 127.0.0.1
och är avsedd för en användare på en betrodd dator. Lagra data på en åtkomstskyddad disk.
Exponera inte servern på internet eller i kontorsnätet. Mobiluppladdning över nätet är en senare funktion.

## Vad som behöver verifieras innan skarp drift

1. Windows-installation och utskrift i den faktiska Excel-versionen.
2. Liveavläsning med valt API-konto och modell.
3. 5–10 ritningar med manuellt kontrollerat facit: saknade mätpunkter, felkopplade don,
   överstrykningar, enheter och rumssummeringar. De tidigare AI-genererade protokollen är inte ett verifierat facit.
4. Tid för granskning jämfört med manuell avskrift. Anpassa avläsningen efter resultaten.

## Utveckling

```powershell
git init
git add .
git commit -m "Initial local Luftprotokoll pilot"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Git-ignore undantar projektdata, ritningar, API-inställningar och genererade dokument.
Ingen serverinstallation, Docker eller Node behövs för denna första version.
På macOS/Linux: skapa en Python-miljö, installera requirements och kör `python app.py --open`.

API-underlag: https://developers.openai.com/api/docs/guides/file-inputs
och https://developers.openai.com/api/docs/guides/structured-outputs
