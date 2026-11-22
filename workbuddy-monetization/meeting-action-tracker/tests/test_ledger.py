import copy
import importlib.util
import json
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('checker', ROOT / 'scripts/check_ledger.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'assets/demo.json').read_text(encoding='utf-8'))

    def run_check(self):
        return module.check(self.data, date(2026, 11, 7))

    def test_missing_info_is_valid_draft_never_ready(self):
        result = self.run_check()
        self.assertTrue(result['valid'], result['errors'])
        self.assertFalse(any(t['ready'] for t in result['tasks']))
        self.assertTrue(result['tasks'][1]['blocked'])

    def test_invented_owner_without_evidence_rejected(self):
        self.data['tasks'][2]['owner'] = '王五'
        self.assertFalse(self.run_check()['valid'])

    def test_broken_quote_rejected(self):
        self.data['tasks'][0]['evidence'][0]['quote'] = '我已接受任务'
        self.assertFalse(self.run_check()['valid'])

    def test_dangling_dependency_rejected(self):
        self.data['tasks'][1]['depends_on'] = ['T999']
        self.assertFalse(self.run_check()['valid'])

    def test_cycle_rejected(self):
        task = self.data['tasks'][0]
        task['dependency_state'] = 'explicit'
        task['depends_on'] = ['T002']
        task['evidence'][0]['supports'].append('dependency')
        self.assertTrue(any('cycle' in e for e in self.run_check()['errors']))

    def test_done_needs_progress_evidence(self):
        self.data['tasks'][0]['status'] = 'done'
        self.assertFalse(self.run_check()['valid'])

    def test_day_deadline_not_overdue_at_midnight(self):
        task = self.data['tasks'][0]
        task['due'] = {'raw': '11月7日', 'date': '2026-11-07', 'basis': '测试日期'}
        task['evidence'][0]['supports'].append('due')
        self.assertEqual(self.run_check()['tasks'][0]['timing'], 'due_today')
        task['due']['date'] = '2026-11-06'
        self.assertEqual(self.run_check()['tasks'][0]['timing'], 'overdue')

    def test_invalid_ledger_cannot_claim_ready(self):
        self.data['tasks'].append(copy.deepcopy(self.data['tasks'][0]))
        result = self.run_check()
        self.assertFalse(result['valid'])
        self.assertFalse(any(t['ready'] for t in result['tasks']))


if __name__ == '__main__':
    unittest.main()
