"""Synthetic fixtures have known truth; not real Office application acceptance."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from xml.sax.saxutils import escape
import zipfile
from numeric_prototype import extract, recompute

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FIXTURES = HERE / 'fixtures'
FIXTURES.mkdir(exist_ok=True)
checks = []


def check(name, passed):
    assert passed, name
    checks.append(name)


def rejected(name, function):
    try:
        function()
    except (ValueError, KeyError, zipfile.BadZipFile):
        checks.append(name)
    else:
        raise AssertionError(name)


csv_path = FIXTURES / 'source.csv'
csv_path.write_text('status,amount\n已完成,1000\n已完成,200\n已完成,34.56\n进行中待复查未完成,99999\n', encoding='utf-8')
# Ground truth is authored independently of the extraction/recalculation functions.
truth = {'docx': ['3', '1234.65', '411.52'], 'pptx': ['3', '1234.56', '411.52']}
for extension, namespace, prefix, part in [
    ('docx', 'http://schemas.openxmlformats.org/wordprocessingml/2006/main', 'w', 'word/document.xml'),
    ('pptx', 'http://schemas.openxmlformats.org/drawingml/2006/main', 'a', 'ppt/slides/slide1.xml')]:
    values = truth[extension]
    paragraphs = [f'<{prefix}:p><{prefix}:r><{prefix}:t>{escape(label)}</{prefix}:t></{prefix}:r><{prefix}:r><{prefix}:t>{value}</{prefix}:t></{prefix}:r></{prefix}:p>'
                  for label, value in zip(['完成数：', '金额：', '平均：'], values)]
    if extension == 'docx':
        content = paragraphs[0] + '<w:tbl><w:tr><w:tc>' + ''.join(paragraphs[1:]) + '</w:tc></w:tr></w:tbl>'
    else:
        content = paragraphs[0] + '<a:tbl><a:tr><a:tc><a:txBody>' + ''.join(paragraphs[1:]) + '</a:txBody></a:tc></a:tr></a:tbl>'
    path = FIXTURES / f'synthetic.{extension}'
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr(part, f'<root xmlns:{prefix}="{namespace}">{content}</root>')
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    records = extract(path)
    check(f'{extension}_body_table_numbers_3_of_3', [row['value'] for row in records] == values)
    check(f'{extension}_unmapped_not_guessed', all(row['mapping_state'] == 'unmapped' for row in records))
    check(f'{extension}_source_bytes_unchanged', hashlib.sha256(path.read_bytes()).hexdigest() == before)

claims = [
    {'field': 'status', 'where': {'status': '已完成'}, 'operation': 'count', 'reported': '3', 'source_unit': '个', 'report_unit': '个'},
    {'field': 'amount', 'where': {'status': '已完成'}, 'operation': 'sum', 'reported': '1234.65', 'source_unit': '元', 'report_unit': '元'},
    {'field': 'amount', 'where': {'status': '已完成'}, 'operation': 'mean', 'reported': '411.52', 'source_unit': '元', 'report_unit': '元'},
]
results = [recompute(csv_path, claim) for claim in claims]
check('three_recomputed_truth_values', [row['recomputed'] for row in results] == ['3', '1234.56', '411.52'])
check('wrong_amount_flagged', [row['state'] for row in results] == ['matches', 'difference', 'matches'])
check('exact_status_excludes_substring_false_positive', all(row['matched_rows'] == 3 for row in results))
rejected('unknown_field_rejected', lambda: recompute(csv_path, {**claims[0], 'field': 'missing'}))
rejected('unit_mismatch_rejected', lambda: recompute(csv_path, {**claims[1], 'report_unit': '万元'}))
rejected('empty_mean_rejected', lambda: recompute(csv_path, {**claims[2], 'where': {'status': '不存在'}}))
bad = FIXTURES / 'bad.pptx'; bad.write_text('not a zip', encoding='utf-8')
rejected('corrupt_package_rejected', lambda: extract(bad))
(FIXTURES / 'truth.json').write_text(json.dumps(truth, ensure_ascii=False, indent=2), encoding='utf-8')
(HERE / 'recalculation.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')

runtime = HERE / 'learning-demo'
env = {**os.environ, 'LEARNING_COACH_DATA_DIR': str(runtime), 'PYTHONIOENCODING': 'utf-8'}
run = subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'learning-coach/scripts/generate_practice.py'), '--grade', '4', '--date', '2026-11-20'], env=env, capture_output=True, text=True, encoding='utf-8')
(HERE / 'learning-preview.log').write_text(run.stdout + run.stderr, encoding='utf-8')
check('grade4_preview_process_success', run.returncode == 0)
html = sorted((runtime / 'outputs').glob('*.html'))[-1].read_text(encoding='utf-8')
check('preview_two_pages_five_questions_five_answers', html.count('class="page"') == 2 and html.count('class="q"') == 5 and html.count('class="a"') == 5)
check('no_nickname_profile_or_history_ledger', not (runtime / 'profiles.json').exists() and not (runtime / 'ledger.json').exists())
summary = {'interpreter': sys.executable, 'python': sys.version, 'checks_passed': len(checks), 'checks': checks,
           'numeric_coverage': {'synthetic_truth_numbers': 6, 'matched_numbers': 6, 'ratio': 1.0},
           'recomputed_metrics': 3, 'fixtures_kind': 'minimal OOXML body/table fixtures, not full real Office documents',
           'limitations': ['explicit metric mappings required; no automatic business inference', 'OCR, charts, dates, IDs, thousands separators and real file coverage not accepted', 'real Office opening/rendering and PDF printing not tested', 'no online listing changes, uploads or paid skill execution']}
(HERE / 'validation.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))
