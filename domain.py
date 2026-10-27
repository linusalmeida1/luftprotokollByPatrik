"""Validation and calculations. No AI decisions are trusted as approval."""
import math
import uuid

TEXT_FIELDS = ('building', 'floor', 'system', 'room', 'room_name', 'device', 'scope', 'evidence')
UNITS = ('', 'l/s', 'm³/h')

def number(value):
    if value is None or value == '':
        return None
    if isinstance(value, bool):
        raise ValueError('Ett flöde måste vara ett tal.')
    try:
        result = float(str(value).replace(',', '.'))
    except (TypeError, ValueError):
        raise ValueError('Ogiltigt flöde.') from None
    if not math.isfinite(result) or result < 0 or result > 1_000_000:
        raise ValueError('Flödet måste vara mellan 0 och 1 000 000.')
    return result

def normalize_row(data):
    if not isinstance(data, dict):
        raise ValueError('Ogiltig mätpost.')
    row = {key: str(data.get(key) or '')[:1000 if key == 'evidence' else 150] for key in TEXT_FIELDS}
    row['id'] = str(data.get('id') or uuid.uuid4().hex)
    if len(row['id']) > 100:
        raise ValueError('Ogiltigt post-ID.')
    row['direction'] = data.get('direction', 'T')
    if row['direction'] not in ('T', 'F'):
        raise ValueError('Luftslag måste vara T eller F.')
    for kind in ('design', 'measured'):
        row[kind] = number(data.get(kind))
        row[kind + '_unit'] = data.get(kind + '_unit', '')
        if row[kind + '_unit'] not in UNITS:
            raise ValueError('Välj l/s eller m³/h.')
    page = number(data.get('source_page', 1))
    if page is None or page < 1 or page != int(page) or page > 10000:
        raise ValueError('Källsidan måste vara ett positivt heltal.')
    row['source_page'] = int(page)
    row['source_file'] = str(data.get('source_file') or '')[:100]
    row['reviewed'] = data.get('reviewed') is True
    row['excluded'] = data.get('excluded') is True
    return row

def to_ls(value, unit):
    if value is None or unit not in ('l/s', 'm³/h'):
        return None
    return value / 3.6 if unit == 'm³/h' else value

def calculate(row):
    design = to_ls(row['design'], row['design_unit'])
    measured = to_ls(row['measured'], row['measured_unit'])
    percentage = measured / design if design is not None and design > 0 and measured is not None else None
    issues = []
    if not row['room'].strip(): issues.append('Rumsnummer saknas')
    if row['measured'] is None: issues.append('Mätvärde saknas')
    elif not row['measured_unit']: issues.append('Mätenhet saknas')
    if row['design'] is not None and not row['design_unit']: issues.append('Projekterad enhet saknas')
    if not row['scope'].strip(): issues.append('Mätomfattning saknas')
    if not row['reviewed']: issues.append('Inte granskad')
    return {'design_ls': design, 'measured_ls': measured, 'percentage': percentage, 'issues': issues}

def export_rows(rows, draft=False):
    # Blank is not zero. An unreadable candidate must be explicitly excluded or resolved.
    candidates = [r for r in rows if not r['excluded']]
    unresolved = [r for r in candidates if calculate(r)['issues']]
    if unresolved and not draft:
        raise ValueError(f'{len(unresolved)} mätposter behöver granskas, kompletteras eller uteslutas.')
    measured = [r for r in candidates if r['measured'] is not None]
    if not measured:
        raise ValueError('Det finns inga registrerade mätvärden att exportera.')
    return measured
