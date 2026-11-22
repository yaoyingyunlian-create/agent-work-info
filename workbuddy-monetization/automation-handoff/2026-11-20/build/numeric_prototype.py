"""Local feasibility prototype. No implicit inference of business metrics."""
import csv
from decimal import Decimal, InvalidOperation
import importlib.util
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('existing_inspector', ROOT / 'artifact-verifier/scripts/inspect_artifact.py')
inspector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspector)
NUMBER = re.compile(r'(?<![A-Za-z0-9_.])-?\d+(?:\.\d+)?(?![A-Za-z0-9_.])')


def extract(path):
    path = Path(path)
    records = []
    if path.suffix.lower() not in ('.docx', '.pptx') or path.stat().st_size > 10_000_000:
        raise ValueError('Expected DOCX/PPTX up to 10 MB')
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len({x.filename for x in entries}) != len(entries) or sum(x.file_size for x in entries) > 20_000_000:
            raise ValueError('Duplicate parts or expanded size limit exceeded')
        if any(x.flag_bits & 1 for x in entries):
            raise ValueError('Encrypted entries unsupported')
        parts = [n for n in archive.namelist() if n == 'word/document.xml' or re.fullmatch(r'ppt/slides/slide\d+\.xml', n)]
        if not parts:
            raise ValueError('No supported content parts')
        for part in sorted(parts):
            root = ET.fromstring(archive.read(part))
            ns = inspector.WORD if part.startswith('word/') else inspector.DRAWING
            for index, paragraph in enumerate(root.iter(ns + 'p'), 1):
                text = inspector.paragraph_text(paragraph, ns)
                for match in NUMBER.finditer(text):
                    records.append({'part': part, 'paragraph': index, 'offset': match.start(),
                                    'value': match.group(), 'text': text, 'mapping_state': 'unmapped'})
    return records


def recompute(csv_path, claim):
    """Claim supplies field, exact equality filter, operation, units and reported value."""
    with open(csv_path, encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError('Missing or duplicate headers')
        field, where = claim['field'], claim['where']
        if not {field, *where} <= set(reader.fieldnames):
            raise ValueError('Unknown field')
        selected = []
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError('Malformed CSV row')
            if all(row[key] == value for key, value in where.items()):
                selected.append(row)
    if claim.get('source_unit') != claim.get('report_unit') or not claim.get('source_unit'):
        raise ValueError('Explicit matching units required')
    operation = claim['operation']
    if operation == 'count':
        value = Decimal(len(selected))
    elif operation in ('sum', 'mean'):
        try:
            values = [Decimal(row[field]) for row in selected]
        except InvalidOperation as exc:
            raise ValueError('Invalid decimal value') from exc
        if not all(value.is_finite() for value in values):
            raise ValueError('Non-finite value')
        if operation == 'mean' and not values:
            raise ValueError('Cannot average an empty selection')
        value = sum(values, Decimal(0))
        if operation == 'mean':
            value /= len(values)
    else:
        raise ValueError('Unsupported operation')
    reported = Decimal(claim['reported'])
    if not reported.is_finite():
        raise ValueError('Non-finite reported value')
    return {'field': field, 'condition': where, 'operation': operation,
            'matched_rows': len(selected), 'recomputed': str(value),
            'reported': str(reported), 'unit': claim['source_unit'],
            'state': 'matches' if value == reported else 'difference'}
    if claim['operation'] == 'count':
        value = Decimal(len(selected))
    else:
        values = [Decimal(row[field]) for row in selected]
        if not all(value.is_finite() for value in values):
            raise ValueError('Non-finite value')
        if claim['operation'] == 'sum':
            value = sum(values, Decimal(0))
        elif claim['operation'] == 'mean' and values:
            value = sum(values, Decimal(0)) / len(values)
        else:
            raise ValueError('Unsupported operation or empty mean')
    if claim['source_unit'] != claim['reported_unit']:
        raise ValueError('Unit conversion not declared; cannot compare')
    reported = Decimal(claim['reported'])
    if not reported.is_finite():
        raise ValueError('Non-finite reported value')
    return {'field': field, 'condition': where, 'operation': claim['operation'],
            'recomputed_value': str(value), 'reported_value': str(reported),
            'unit': claim['source_unit'], 'state': 'match' if value == reported else 'difference',
            'delta': str(reported - value)}
