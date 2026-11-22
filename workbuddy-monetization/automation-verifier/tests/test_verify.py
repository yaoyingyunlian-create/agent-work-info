import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('verify', ROOT / 'scripts' / 'verify.py')
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.file = self.base / 'output.csv'
        self.write('id,updated_at\n0,2026-11-06T09:30:00+08:00\n')
        self.data = {'as_of': '2026-11-06T18:00:00+08:00', 'tasks': [{'id': 't', 'name': '测试', 'runs': [{
            'id': 'r', 'start': '2026-11-06T09:00:00+08:00', 'due': '2026-11-06T10:00:00+08:00',
            'artifact': 'output.csv', 'claimed_status': 'success', 'claim_source': '模拟导出',
            'checks': {'mtime': True, 'format': 'csv', 'min_rows': 1, 'required_fields': ['id', 'updated_at'],
                       'data_time_field': 'updated_at'}}]}]}
        self.run_data = self.data['tasks'][0]['runs'][0]

    def write(self, text):
        self.file.write_text(text, encoding='utf-8')
        stamp = verify.timestamp('2026-11-06T09:40:00+08:00').timestamp()
        os.utime(self.file, (stamp, stamp))

    def status(self):
        return verify.audit(self.data, self.base)['entries'][0]['status']

    def test_good_and_sources_unchanged(self):
        before = self.file.read_bytes(), self.file.stat().st_mtime_ns
        self.assertEqual(self.status(), 'verified')
        self.assertEqual(before, (self.file.read_bytes(), self.file.stat().st_mtime_ns))

    def test_empty_success_is_false(self):
        self.write('id,updated_at\n')
        self.assertEqual(self.status(), 'false_success')

    def test_missing_success_is_false(self):
        self.run_data['artifact'] = 'missing.csv'
        self.assertEqual(self.status(), 'false_success')

    def test_missing_without_claim_is_manual(self):
        self.run_data['artifact'] = 'missing.csv'
        self.run_data['claimed_status'] = 'unknown'
        self.assertEqual(self.status(), 'manual')

    def test_bad_encoding_is_manual(self):
        self.file.write_bytes(b'\xff\xfe')
        self.assertEqual(self.status(), 'manual')

    def test_reused_artifact_never_green(self):
        other = copy.deepcopy(self.run_data)
        other['id'] = 'r2'
        self.data['tasks'][0]['runs'].append(other)
        self.assertTrue(all(r['status'] == 'manual' for r in verify.audit(self.data, self.base)['entries']))

    def test_no_rules_is_manual(self):
        del self.run_data['checks']
        self.assertEqual(self.status(), 'manual')

    def test_old_content_with_new_mtime(self):
        self.write('id,updated_at\n1,2026-11-05T09:30:00+08:00\n')
        self.assertEqual(self.status(), 'false_success')

    def test_blank_field(self):
        self.write('id,updated_at\n ,2026-11-06T09:30:00+08:00\n')
        self.assertEqual(self.status(), 'false_success')

    def test_naive_timestamp_rejected(self):
        self.data['as_of'] = '2026-11-06T18:00:00'
        with self.assertRaises(ValueError):
            verify.audit(self.data, self.base)

    def test_future_and_window_boundary_excluded(self):
        self.run_data['start'] = '2026-11-07T09:00:00+08:00'
        self.run_data['due'] = '2026-11-07T10:00:00+08:00'
        report = verify.audit(self.data, self.base)
        self.assertEqual(report['entries'], [])
        self.assertEqual(report['excluded'][0]['reason'], '未到期')

    def test_no_runs_does_not_imply_green(self):
        self.data['tasks'][0]['runs'] = []
        report = verify.audit(self.data, self.base)
        self.assertEqual(report['tasks_without_due_runs'], ['t'])
        self.assertEqual(sum(report['counts'].values()), 0)

    def test_json_false_and_zero_are_valid(self):
        self.file = self.base / 'output.json'
        self.write('[{"id":0,"flag":false}]')
        self.run_data['artifact'] = 'output.json'
        self.run_data['checks'] = {'mtime': True, 'format': 'json', 'min_rows': 1, 'required_fields': ['id', 'flag']}
        self.assertEqual(self.status(), 'verified')

    def test_text_and_html_escaping(self):
        self.run_data['checks'] = {'mtime': True, 'format': 'text', 'min_rows': 1, 'required_fields': []}
        self.data['tasks'][0]['name'] = '<script>alert(1)</script>'
        report = verify.audit(self.data, self.base)
        out = self.base / 'report'
        verify.render(report, out)
        self.assertIn('&lt;script&gt;', (out / 'report.html').read_text(encoding='utf-8'))
        with self.assertRaises(FileExistsError):
            verify.render(report, out)

    def test_success_needs_claim_source(self):
        del self.run_data['claim_source']
        with self.assertRaises(ValueError):
            verify.audit(self.data, self.base)

    def test_malformed_json_is_manual_even_if_claimed_success(self):
        self.run_data['checks']['format'] = 'json'
        self.assertEqual(self.status(), 'manual')


if __name__ == '__main__':
    unittest.main()
