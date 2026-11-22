"""Collect read-only structural evidence. The skill performs semantic review."""
import argparse
import csv
import json
import math
from pathlib import Path
import posixpath
import re
import stat
from urllib.parse import unquote
import xml.etree.ElementTree as ET
import zipfile


PRESENTATION = 'http://schemas.openxmlformats.org/presentationml/2006/main'
DRAWING = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
WORD = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
SPREADSHEET = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
CHART = 'http://schemas.openxmlformats.org/drawingml/2006/chart'
CHART_EX = 'http://schemas.microsoft.com/office/drawing/2014/chartex'
REL_ID = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
CHART_PATH = re.compile(r'(?:ppt|word|xl)/charts/chart(?!Ex)[^/]*\.xml')
S = f'{{{SPREADSHEET}}}'
MATCH_SAMPLE_LIMIT = 20


def paragraph_text(paragraph, namespace):
    def fragments(node):
        for child in node:
            if child.tag == namespace + 't':
                yield child.text or ''
            elif child.tag == namespace + 'tab':
                yield '\t'
            elif child.tag in (namespace + 'br', namespace + 'cr'):
                yield '\n'
            elif child.tag not in (namespace + 'p', WORD + 'del', WORD + 'moveFrom'):
                yield from fragments(child)

    return ''.join(fragments(paragraph))


def record_text_matches(matches, text, **location):
    for result in matches:
        offset = text.find(result['query'])
        if offset < 0:
            continue
        result['matching_blocks'] += 1
        if len(result['samples']) < MATCH_SAMPLE_LIMIT:
            end = offset + len(result['query'])
            result['samples'].append({
                **location, 'offset': offset,
                'excerpt': text[max(0, offset - 60):end + 60],
            })


def search_paragraphs(root, namespace, matches, **location):
    for number, paragraph in enumerate(root.iter(namespace + 'p'), 1):
        record_text_matches(matches, paragraph_text(paragraph, namespace),
                            paragraph=number, **location)


def relationships(archive, part):
    folder, name = posixpath.split(part)
    rels = posixpath.join(folder, '_rels', name + '.rels')
    if rels not in archive.namelist():
        return {}
    return {
        element.attrib['Id']: posixpath.normpath(
            posixpath.join('/' + folder, unquote(element.attrib['Target']))
        ).lstrip('/')
        for element in ET.fromstring(archive.read(rels))
        if element.get('TargetMode') != 'External'
    }


def part_links(archive, part, root, tags):
    relations = relationships(archive, part)
    return [
        {'relationship_id': node.get(REL_ID), 'part': relations.get(node.get(REL_ID)),
         'target_present': relations.get(node.get(REL_ID)) in archive.namelist()}
        for node in root.iter() if node.tag in tags
    ]


def chart_links(archive, part, root):
    return part_links(archive, part, root, (f'{{{CHART}}}chart', f'{{{CHART_EX}}}chart'))


def sheet_drawings(archive, part, root):
    drawings = part_links(archive, part, root, (f'{S}drawing',))
    for drawing in drawings:
        if drawing['target_present']:
            drawing_part = drawing['part']
            try:
                drawing_root = ET.fromstring(archive.read(drawing_part))
                drawing['charts'] = chart_links(archive, drawing_part, drawing_root)
            except ET.ParseError as exc:
                drawing.update(status='read_error', detail=str(exc))
    return drawings


def worksheet_header(root, row_number, shared_strings):
    row = root.find(f"{S}sheetData/{S}row[@r='{row_number}']")
    fields = []
    if row is None:
        return fields
    for cell in row.findall(f'{S}c'):
        value = cell_value(cell, shared_strings)
        formula = cell.find(f'{S}f')
        if value.strip() or formula is not None:
            fields.append({'cell': cell.get('r'), 'value': value,
                           'formula': formula.text if formula is not None else None})
    return fields


def cell_value(cell, shared_strings):
    value = cell.findtext(f'{S}v') or ''
    kind = cell.get('t')
    if kind == 's':
        if not value.isdecimal() or int(value) >= len(shared_strings):
            raise ValueError(f'Invalid shared string at {cell.get("r")}')
        return shared_strings[int(value)]
    if kind == 'inlineStr':
        return spreadsheet_text(cell.find(f'{S}is'))
    return value


def record_cells(root, requests, shared_strings):
    wanted = {request['cell']: request for request in requests}
    for request in requests:
        request['status'] = 'cell_not_stored'
    for cell in root.iterfind(f'{S}sheetData/{S}row/{S}c'):
        request = wanted.get(cell.get('r'))
        if request is None:
            continue
        try:
            value = cell_value(cell, shared_strings)
        except ValueError as exc:
            request.update(status='read_error', detail=str(exc))
            continue
        formula = cell.find(f'{S}f')
        request.update(status='stored', value=value, cell_type=cell.get('t', 'n'),
                       style_index=cell.get('s'))
        if formula is not None:
            request.update(formula=formula.text, formula_attributes=dict(formula.attrib),
                           cache_present=bool(cell.findtext(f'{S}v')))


def spreadsheet_text(element):
    if element is None:
        return ''
    nodes = element.findall(f'{S}t') + element.findall(f'{S}r/{S}t')
    return ''.join(node.text or '' for node in nodes)


def is_numeric_point(value):
    try:
        return math.isfinite(float(value))
    except ValueError:
        return False


def inspect_chart(archive, name):
    try:
        root = ET.fromstring(archive.read(name))
    except ET.ParseError as exc:
        return {'part': name, 'status': 'read_error', 'detail': str(exc)}
    if root.tag != f'{{{CHART}}}chartSpace':
        return {'part': name, 'status': 'unsupported_chart_namespace'}
    results = []
    for series in root.iter(f'{{{CHART}}}ser'):
        values = [
            point.text for field in ('val', 'yVal')
            for element in series.findall(f'{{{CHART}}}{field}')
            for point in element.findall(f'.//{{{CHART}}}pt/{{{CHART}}}v')
            if point.text and point.text.strip()
        ]
        references = [
            formula.text for formula in series.iter(f'{{{CHART}}}f')
            if formula.text and formula.text.strip()
        ]
        value_references = [
            formula.text for field in ('val', 'yVal')
            for element in series.findall(f'{{{CHART}}}{field}')
            for formula in element.iter(f'{{{CHART}}}f')
            if formula.text and formula.text.strip()
        ]
        numeric_count = sum(is_numeric_point(value) for value in values)
        results.append({'nonblank_cached_value_count': len(values),
                        'numeric_cached_value_count': numeric_count,
                        'invalid_cached_value_count': len(values) - numeric_count,
                        'references': references,
                        'value_references': value_references})
    return {'part': name, 'series_count': len(results), 'series': results}


def inspect_office(path, report, header_row, cell_requests, matches):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate package part names')
        main = {'.pptx': 'ppt/presentation.xml', '.xlsx': 'xl/workbook.xml',
                '.docx': 'word/document.xml'}[path.suffix.lower()]
        root = ET.fromstring(archive.read(main))
        related = relationships(archive, main)
        if main.startswith('ppt/'):
            if root.tag != f'{{{PRESENTATION}}}presentation':
                raise ValueError('Unsupported presentation namespace or root')
            slide_ids = root.findall(f'{{{PRESENTATION}}}sldIdLst/{{{PRESENTATION}}}sldId')
            report['declared_slide_count'] = len(slide_ids)
            report['slides'] = []
            for number, slide_id in enumerate(slide_ids, 1):
                part = related.get(slide_id.get(REL_ID))
                slide = {'number': number, 'part': part, 'target_present': part in names}
                if part in names:
                    try:
                        slide_root = ET.fromstring(archive.read(part))
                    except ET.ParseError as exc:
                        slide.update(status='read_error', detail=str(exc))
                        report['slides'].append(slide)
                        continue
                    slide['hidden'] = slide_root.get('show') in ('0', 'false')
                    if matches:
                        search_paragraphs(slide_root, DRAWING, matches,
                                          slide=number, part=part, hidden=slide['hidden'])
                    slide['charts'] = chart_links(archive, part, slide_root)
                report['slides'].append(slide)
        if main.startswith('xl/'):
            if root.tag != f'{{{SPREADSHEET}}}workbook':
                raise ValueError('Unsupported workbook namespace or root')
            sheets = root.findall(f'{{{SPREADSHEET}}}sheets/{{{SPREADSHEET}}}sheet')
            strings_part = 'xl/sharedStrings.xml'
            shared_strings = [
                spreadsheet_text(item) for item in ET.fromstring(archive.read(strings_part))
            ] if strings_part in names else []
            report['declared_sheets'] = []
            if cell_requests:
                report['requested_cells'] = [
                    {'sheet': sheet, 'cell': cell, 'status': 'sheet_not_declared'}
                    for sheet, cell in dict.fromkeys(cell_requests)
                ]
            for sheet in sheets:
                part = related.get(sheet.get(REL_ID))
                evidence = {'name': sheet.get('name'), 'state': sheet.get('state', 'visible'),
                            'part': part, 'target_present': part in names}
                requests = [entry for entry in report.get('requested_cells', [])
                            if entry['sheet'] == evidence['name']]
                for entry in requests:
                    entry['status'] = 'worksheet_unavailable'
                if part in names:
                    sheet_root = ET.fromstring(archive.read(part))
                    evidence['drawings'] = sheet_drawings(archive, part, sheet_root)
                    if sheet_root.tag == f'{S}worksheet':
                        if requests:
                            record_cells(sheet_root, requests, shared_strings)
                        evidence['header_row'] = header_row
                        evidence['header_fields'] = worksheet_header(
                            sheet_root, header_row, shared_strings
                        )
                report['declared_sheets'].append(evidence)
        if main.startswith('word/'):
            if root.tag != WORD + 'document':
                raise ValueError('Unsupported document namespace or root')
            body = root.find(WORD + 'body')
            if body is None:
                raise ValueError('Document body is missing')
            if matches:
                search_paragraphs(body, WORD, matches, part=main)
            report['document_body_charts'] = chart_links(archive, main, root)
        report['classic_chart_parts'] = [
            inspect_chart(archive, name) for name in sorted(names) if CHART_PATH.fullmatch(name)
        ]
        report['extended_chart_parts'] = [
            name for name in sorted(names)
            if re.fullmatch(r'(?:ppt|word|xl)/charts/chartEx[^/]*\.xml', name)
        ]


def inspect(path, header_row=1, cell_requests=(), text_queries=()):
    report = {'path': str(path)}
    try:
        info = path.stat()
        report['exists'] = True
        if not stat.S_ISREG(info.st_mode):
            report['status'] = 'not_regular_file'
            return report
        report['bytes'] = info.st_size
        if not info.st_size:
            report['status'] = 'empty_file'
            return report
        suffix = path.suffix.lower()
        matches = [{'query': query, 'matching_blocks': 0, 'samples': []}
                   for query in dict.fromkeys(text_queries)]
        if suffix in ('.pptx', '.docx', '.xlsx'):
            inspect_office(path, report, header_row, cell_requests, matches)
        elif suffix in ('.csv', '.tsv'):
            with path.open(encoding='utf-8-sig', newline='') as source:
                rows = csv.reader(source, delimiter='\t' if suffix == '.tsv' else ',', strict=True)
                report['header'] = next(rows, [])
                report['nonblank_data_rows'] = 0
                report['column_count_mismatch_rows'] = []
                for number, row in enumerate(rows, 2):
                    if any(cell.strip() for cell in row):
                        report['nonblank_data_rows'] += 1
                        if len(row) != len(report['header']):
                            report['column_count_mismatch_rows'].append(number)
        elif suffix in ('.md', '.txt'):
            lines = path.read_text(encoding='utf-8-sig').splitlines()
            report['nonblank_lines'] = sum(bool(line.strip()) for line in lines)
            if matches:
                for number, line in enumerate(lines, 1):
                    record_text_matches(matches, line, line=number)
        else:
            report['status'] = 'requires_viewer'
            return report
        report['status'] = 'structure_read'
        if matches:
            report['text_matches'] = matches
            if suffix == '.pptx':
                report['text_unavailable_slides'] = [
                    slide['number'] for slide in report['slides']
                    if not slide['target_present'] or slide.get('status') == 'read_error'
                ]
    except FileNotFoundError as exc:
        report['status'] = 'read_error' if report.get('exists') else 'missing'
        report['detail'] = str(exc)
        report.setdefault('exists', False)
    except (OSError, KeyError, ValueError, csv.Error, ET.ParseError,
            zipfile.BadZipFile, RuntimeError) as exc:
        report.update(status='read_error', detail=str(exc))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', type=Path, nargs='+')
    parser.add_argument('--header-row', type=int, default=1, help='Excel header row (1-based)')
    parser.add_argument('--cell', nargs=2, action='append', default=[], metavar=('SHEET', 'A1'),
                        help='Record an Excel cell by exact sheet name and A1 address')
    parser.add_argument('--find', action='append', default=[], metavar='TEXT',
                        help='Locate literal text in PPTX, DOCX, Markdown or TXT')
    args = parser.parse_args()
    if args.header_row < 1:
        parser.error('--header-row must be positive')
    cells = []
    for sheet, address in args.cell:
        match = re.fullmatch(r'\$?([A-Za-z]{1,3})\$?([1-9][0-9]{0,6})', address)
        if not match:
            parser.error('--cell requires an A1 cell address')
        column, row = match.groups()
        column = column.upper()
        if int(row) > 1048576 or (len(column) == 3 and column > 'XFD'):
            parser.error('--cell address is outside the Excel worksheet')
        cells.append((sheet, column + row))
    if cells and any(path.suffix.lower() != '.xlsx' for path in args.paths):
        parser.error('--cell applies to .xlsx files')
    if any(not query.strip() for query in args.find):
        parser.error('--find requires nonblank text')
    if args.find and any(path.suffix.lower() not in ('.pptx', '.docx', '.md', '.txt')
                         for path in args.paths):
        parser.error('--find applies to PPTX, DOCX, Markdown and TXT')
    print(json.dumps([inspect(path, args.header_row, cells, args.find) for path in args.paths],
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
