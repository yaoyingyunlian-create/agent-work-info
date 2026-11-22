import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from onboarding import guide
from common import InputError


class Onboarding(unittest.TestCase):
    def test_first_visit_is_short(self):
        result = guide()
        self.assertEqual([q['key'] for q in result['questions']], ['profile', 'goal', 'materials'])
        self.assertEqual(result['next_action'], 'ask_questions')

    def test_known_data_not_reasked(self):
        result = guide({'profile': 'senior', 'goal': 'new', 'mode': 'weekly_template',
                        'calendar': {'weekdays': [0, 1, 2, 3, 4]},
                        'demands': [{'id': 'A'}], 'slots': [{'id': 'P1'}], 'rules': [{'id': 'fixed'}]})
        self.assertEqual(result['questions'], [])
        self.assertEqual(result['next_action'], 'precheck')
        self.assertTrue(any('连堂' in s for s in result['reminders']))

    def test_template_does_not_demand_full_data(self):
        result = guide({'profile': 'primary', 'goal': 'template'})
        self.assertEqual(result['next_action'], 'create_template')
        self.assertEqual(result['questions'], [])

    def test_training_and_adjustment_are_specific(self):
        result = guide({'profile': 'training', 'goal': 'adjust', 'materials': 'schedule', 'mode': 'date_range'})
        self.assertLessEqual(len(result['questions']), 3)
        self.assertIn('change_request', result['remaining_question_keys'])
        self.assertTrue(any('课时单位' in s for s in result['reminders']))
        with self.assertRaises(InputError):
            guide({'profile': 'typo'})
        with self.assertRaises(InputError):
            guide([])

    def test_no_args_works_without_third_party_dependencies(self):
        result = subprocess.run([sys.executable, '-S', '-X', 'utf8', str(ROOT / 'scripts/cli.py')],
                                capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(result.stdout)['questions']), 3)


if __name__ == '__main__':
    unittest.main()
