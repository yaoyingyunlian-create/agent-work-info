import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from inspect_artifact import CHART, DRAWING, PRESENTATION, REL_ID, SPREADSHEET, WORD, inspect

REL_NS = REL_ID[1:].split('}')[0]


def rels(*items):
    return '<Relationships>' + ''.join(
        f'<Relationship Id="{key}" Target="{target}"/>' for key, target in items
    ) + '</Relationships>'


class InspectTest(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name)

    def test_cli_reports_missing_empty_corrupt_and_viewer(self):
        names = ['缺失.csv', '空白.txt', '损坏.pptx', '扫描.pdf']
        for name, content in zip(names[1:], [b'', b'invalid', b'%PDF']):
            (self.root / name).write_bytes(content)
        script = Path(__file__).resolve().parents[1] / 'scripts' / 'inspect_artifact.py'
        result = subprocess.check_output(
            [sys.executable, '-X', 'utf8', str(script)] + [str(self.root / n) for n in names],
            encoding='utf-8',
        )
        self.assertEqual([row['status'] for row in json.loads(result)],
                         ['missing', 'empty_file', 'read_error', 'requires_viewer'])

    def test_csv_quoted_fields_and_blank_row(self):
        path = self.root / '汇总.csv'
        path.write_text('"地区,名称",金额\n华南,0\n,\n华东\n', encoding='utf-8-sig')
        result = inspect(path)
        self.assertEqual(result['header'], ['地区,名称', '金额'])
        self.assertEqual(result['nonblank_data_rows'], 2)
        self.assertEqual(result['column_count_mismatch_rows'], [4])

    def test_slides_and_chart_cache_evidence(self):
        path = self.root / '报告.pptx'
        with ZipFile(path, 'w') as archive:
            archive.writestr('ppt/presentation.xml',
                             f'<presentation xmlns="{PRESENTATION}" xmlns:r="{REL_NS}"><sldIdLst>'
                             '<sldId r:id="s1"/><sldId r:id="s2"/></sldIdLst></presentation>')
            archive.writestr('ppt/_rels/presentation.xml.rels',
                             rels(('s1', 'slides/slide9.xml'), ('s2', 'slides/missing.xml')))
            archive.writestr('ppt/slides/slide9.xml',
                             f'<sld xmlns="{PRESENTATION}" xmlns:c="{CHART}" xmlns:r="{REL_NS}"'
                             f' xmlns:a="{DRAWING[1:-1]}" show="0">'
                             '<a:p><a:r><a:t>退款后</a:t></a:r><a:r><a:t>实收</a:t></a:r></a:p>'
                             '<c:chart r:id="c1"/><c:chart r:id="missing"/></sld>')
            archive.writestr('ppt/slides/_rels/slide9.xml.rels',
                             rels(('c1', '../charts/chart1.xml')))
            archive.writestr('ppt/charts/chart1.xml',
                             f'<chartSpace xmlns="{CHART}"><ser><val><numRef>'
                             '<f>Data!B2</f></numRef></val></ser><ser><val><numLit>'
                             '<pt><v>0</v></pt><pt><v>#N/A</v></pt><pt><v>NaN</v></pt>'
                             '</numLit></val></ser><ser><cat>'
                             '<strRef><f>Data!A2</f></strRef></cat></ser></chartSpace>')
            archive.writestr('ppt/charts/chart2.xml', f'<chartSpace xmlns="{CHART}"/>')
            archive.writestr('ppt/charts/chartEx1.xml', '<chartSpace/>')
        report = inspect(path, text_queries=['退款后实收'])
        self.assertEqual(report['declared_slide_count'], 2)
        first, second = report['classic_chart_parts']
        self.assertEqual(first['series'][0], {'nonblank_cached_value_count': 0,
                                              'numeric_cached_value_count': 0,
                                              'invalid_cached_value_count': 0,
                                              'references': ['Data!B2'],
                                              'value_references': ['Data!B2']})
        self.assertEqual(first['series'][1]['nonblank_cached_value_count'], 3)
        self.assertEqual(first['series'][1]['numeric_cached_value_count'], 1)
        self.assertEqual(first['series'][1]['invalid_cached_value_count'], 2)
        self.assertEqual(first['series'][2]['value_references'], [])
        self.assertEqual(second['series_count'], 0)
        self.assertEqual(report['extended_chart_parts'], ['ppt/charts/chartEx1.xml'])
        slide, missing = report['slides']
        self.assertTrue(slide['hidden'])
        self.assertEqual(slide['number'], 1)
        self.assertEqual([link['target_present'] for link in slide['charts']], [True, False])
        self.assertFalse(missing['target_present'])
        self.assertEqual(report['text_unavailable_slides'], [2])
        self.assertEqual(report['text_matches'][0]['samples'], [
            {'slide': 1, 'part': 'ppt/slides/slide9.xml', 'paragraph': 1,
             'hidden': True, 'offset': 0, 'excerpt': '退款后实收'},
        ])

    def test_text_search_reports_word_paragraphs_and_plain_text_lines(self):
        doc = self.root / '报告.docx'
        with ZipFile(doc, 'w') as archive:
            archive.writestr('word/document.xml', f'<w:document xmlns:w="{WORD[1:-1]}">'
                             '<w:body><w:p><w:r><w:t>统计口径</w:t></w:r></w:p>'
                             '<w:tbl><w:tr><w:tc><w:p><w:del><w:r>'
                             '<w:delText>毛额</w:delText></w:r></w:del>'
                             '<w:r><w:t>实</w:t></w:r><w:r><w:t>收</w:t></w:r>'
                             '</w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
        notes = self.root / '来源.md'
        notes.write_text('# 统计口径\n\n退款后实收\n', encoding='utf-8')
        script = Path(__file__).resolve().parents[1] / 'scripts' / 'inspect_artifact.py'
        output = subprocess.check_output(
            [sys.executable, '-X', 'utf8', str(script), str(doc), str(notes),
             '--find', '实收', '--find', '毛额'], encoding='utf-8',
        )
        word, markdown = json.loads(output)
        self.assertEqual(word['text_matches'][0]['samples'][0]['paragraph'], 2)
        self.assertEqual(word['text_matches'][1]['matching_blocks'], 0)
        self.assertEqual(markdown['text_matches'][0]['samples'][0]['line'], 3)

    def test_excel_header_row_has_cell_anchors(self):
        path = self.root / '明细.xlsx'
        with ZipFile(path, 'w') as archive:
            archive.writestr('xl/workbook.xml',
                             f'<workbook xmlns="{SPREADSHEET}" xmlns:r="{REL_NS}"><sheets>'
                             '<sheet name="明细" r:id="s1"/></sheets></workbook>')
            archive.writestr('xl/_rels/workbook.xml.rels',
                             rels(('s1', '/xl/worksheets/sheet7.xml')))
            archive.writestr('xl/sharedStrings.xml',
                             f'<sst xmlns="{SPREADSHEET}"><si><r><t>实</t></r>'
                             '<r><t>收</t></r></si></sst>')
            archive.writestr('xl/worksheets/sheet7.xml',
                             f'<worksheet xmlns="{SPREADSHEET}"><sheetData><row r="3">'
                             '<c r="A3" t="s"><v>0</v></c><c r="C3" t="inlineStr">'
                             '<is><t>期间</t></is></c><c r="D3"><f>1+2</f></c>'
                             '</row><row r="4"><c r="D4" s="2"><f t="shared" si="0"/>'
                             '<v>0</v></c><c r="E4" t="e"><f>1/0</f><v>#DIV/0!</v></c>'
                             '</row></sheetData></worksheet>')
        sheet = inspect(path, header_row=3)['declared_sheets'][0]
        self.assertEqual(sheet['header_fields'], [
            {'cell': 'A3', 'value': '实收', 'formula': None},
            {'cell': 'C3', 'value': '期间', 'formula': None},
            {'cell': 'D3', 'value': '', 'formula': '1+2'},
        ])
        script = Path(__file__).resolve().parents[1] / 'scripts' / 'inspect_artifact.py'
        output = subprocess.check_output(
            [sys.executable, '-X', 'utf8', str(script), str(path),
             '--cell', '明细', '$d$4', '--cell', '明细', 'D3', '--cell', '明细', 'E4',
             '--cell', '明细', 'B3', '--cell', '缺失', 'A1'],
            encoding='utf-8',
        )
        zero, uncached, error, absent, unknown = json.loads(output)[0]['requested_cells']
        self.assertEqual(zero['value'], '0')
        self.assertEqual(zero['style_index'], '2')
        self.assertEqual(zero['formula_attributes'], {'t': 'shared', 'si': '0'})
        self.assertTrue(zero['cache_present'])
        self.assertFalse(uncached['cache_present'])
        self.assertEqual(uncached['formula'], '1+2')
        self.assertEqual((error['cell_type'], error['value']), ('e', '#DIV/0!'))
        self.assertEqual(absent['status'], 'cell_not_stored')
        self.assertEqual(unknown['status'], 'sheet_not_declared')

    def test_excel_drawing_links_and_corrupt_chart_keep_valid_evidence(self):
        path = self.root / '图表.xlsx'
        with ZipFile(path, 'w') as archive:
            archive.writestr('xl/workbook.xml',
                             f'<workbook xmlns="{SPREADSHEET}" xmlns:r="{REL_NS}"><sheets>'
                             '<sheet name="汇总" r:id="s1"/></sheets></workbook>')
            archive.writestr('xl/_rels/workbook.xml.rels', rels(('s1', 'worksheets/sheet1.xml')))
            archive.writestr('xl/worksheets/sheet1.xml',
                             f'<worksheet xmlns="{SPREADSHEET}" xmlns:r="{REL_NS}">'
                             '<drawing r:id="d1"/><drawing r:id="lost"/></worksheet>')
            archive.writestr('xl/worksheets/_rels/sheet1.xml.rels',
                             rels(('d1', '../drawings/drawing2.xml')))
            archive.writestr('xl/drawings/drawing2.xml',
                             f'<drawing xmlns:c="{CHART}" xmlns:r="{REL_NS}">'
                             '<c:chart r:id="bad"/><c:chart r:id="ok"/></drawing>')
            archive.writestr('xl/drawings/_rels/drawing2.xml.rels',
                             rels(('bad', '../charts/chart1.xml'), ('ok', '../charts/chart2.xml')))
            archive.writestr('xl/charts/chart1.xml', '<broken')
            archive.writestr('xl/charts/chart2.xml', f'<chartSpace xmlns="{CHART}"/>')
        report = inspect(path)
        self.assertEqual(report['status'], 'structure_read')
        drawing, missing = report['declared_sheets'][0]['drawings']
        self.assertEqual([chart['part'] for chart in drawing['charts']],
                         ['xl/charts/chart1.xml', 'xl/charts/chart2.xml'])
        self.assertFalse(missing['target_present'])
        self.assertEqual(report['classic_chart_parts'][0]['status'], 'read_error')
        self.assertEqual(report['classic_chart_parts'][1]['series_count'], 0)


if __name__ == '__main__':
    unittest.main()
