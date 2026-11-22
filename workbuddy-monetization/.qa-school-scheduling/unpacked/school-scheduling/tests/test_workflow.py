from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_assets import examples, base, demand, grade22
from common import InputError, digest, write_json
from normalize_input import normalize
from cp_sat_scheduler import solve
from validate_schedule import validate
from adjust_schedule import adjust
from excel_io import template, import_excel, export
from expand_calendar import expand_calendar
from openpyxl import load_workbook


def refresh(data, solution):
    solution['input_hash'] = digest(data)
    solution['rule_hash'] = digest(data['rules'])
    solution['calendar_hash'] = digest(data['expanded_calendar'])
    solution['solution_hash'] = digest(solution['assignments'])
    return solution


def tiny():
    raw = base('primary')
    raw['calendar']['weekdays'] = [0, 1]
    raw['slots'] = raw['slots'][:2]
    raw['resources'][0]['capacity'] = 2
    raw['demands'] = [demand('A', 'G1', 'T1', count=2), demand('B', 'G2', 'T2', count=1)]
    return raw


class Workflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.examples = {}
        for name, raw in examples().items():
            data = normalize(raw)
            solution = solve(data, 60)
            cls.examples[name] = data, solution, validate(data, solution)

    def test_four_scenarios(self):
        for name, (data, solution, report) in self.examples.items():
            with self.subTest(name=name):
                self.assertIn(solution['status'], ['OPTIMAL', 'FEASIBLE'])
                self.assertTrue(report['ready_for_acceptance'], report['hard_violations'])
                for layer in solution['layers']:
                    if layer['tier'] is not None:
                        expected = sum(r['penalty'] * r['weight'] for r in report['rule_results']
                                       if r.get('enabled') and r.get('level') == 'soft' and r['tier'] == layer['tier'])
                        self.assertEqual(expected, layer['value'])

    def test_template_roundtrip(self):
        for name, (data, _, _) in self.examples.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory(prefix='排课模板') as folder:
                path = Path(folder) / '输入.xlsx'
                template(data, path)
                actual, errors = import_excel(path)
                self.assertFalse(errors, errors)
                self.assertEqual(data, actual)

    def test_import_errors_have_locations(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'input.xlsx'
            template(tiny(), path)
            wb = load_workbook(path)
            wb['教学需求']['B2'] = '=1+1'
            wb.save(path)
            _, errors = import_excel(path)
            self.assertTrue(any(e['sheet'] == '教学需求' and e['row'] == 2 for e in errors))

    def test_unknown_rules_and_ids(self):
        raw = tiny()
        raw['rules'] = [{'id': 'bad', 'type': 'unsupported'}]
        with self.assertRaises(InputError):
            normalize(raw)
        raw['rules'][0]['enabled'] = False
        normalize(raw)
        raw['demands'][0]['teacher_ids'] = ['MISSING']
        with self.assertRaises(InputError):
            normalize(raw)

    def test_excluded_dates_do_not_drop_weekly_quota(self):
        raw = tiny()
        raw['demands'][0]['exclude_dates'] = ['2000-01-03', '2000-01-04']
        solution = solve(normalize(raw), 5)
        self.assertEqual(solution['status'], 'INFEASIBLE')

    def test_fixed_conflict_and_unavailable(self):
        raw = tiny()
        for d in raw['demands']:
            d['teacher_ids'] = ['T1']
            d['fixed'] = [{'session_index': 1, 'weekday': 0, 'slot_id': 'P1'}]
        self.assertEqual(solve(normalize(raw), 5)['status'], 'INFEASIBLE')
        raw = tiny()
        raw['teachers'][0]['availability'] = []
        self.assertEqual(solve(normalize(raw), 5)['status'], 'INFEASIBLE')

    def test_interval_student_and_resource_conflicts(self):
        data, solution, _ = copy.deepcopy(self.examples['senior'])
        a = next(c for c in solution['assignments'] if c['demand_id'] == 'D1')
        b = next(c for c in solution['assignments'] if c['demand_id'] == 'D2')
        for k in ['date', 'weekday', 'week_type', 'start', 'end', 'slot_id', 'half_day']:
            b[k] = a[k]
        report = validate(data, refresh(data, solution))
        self.assertIn('PERSON_CONFLICT', {v['code'] for v in report['hard_violations']})
        data['resources'][0]['capacity'] = 1
        report = validate(data, refresh(data, solution))
        self.assertIn('RESOURCE_CAPACITY', {v['code'] for v in report['hard_violations']})

    def test_travel_and_external_conflict(self):
        raw = tiny()
        raw['demands'] = raw['demands'][:1]
        raw['resources'].append(dict(copy.deepcopy(raw['resources'][0]), id='R2', campus_id='B'))
        raw['demands'][0]['resource_ids'] = []
        raw['demands'][0]['eligible_resource_ids'] = ['R1', 'R2']
        raw['demands'][0]['fixed'] = [{'session_index': 1, 'weekday': 0, 'slot_id': 'P1', 'resource_ids': ['R1']},
                                     {'session_index': 2, 'weekday': 0, 'slot_id': 'P2', 'resource_ids': ['R2']}]
        raw['travel_minutes'] = {'A': {'B': 30}, 'B': {'A': 30}}
        self.assertEqual(solve(normalize(raw), 5)['status'], 'INFEASIBLE')
        raw['travel_minutes']['A']['B'] = 5
        data = normalize(raw)
        solution = solve(data, 5)
        self.assertTrue(validate(data, solution)['valid'])
        data['external_occupancy'] = [{'date': '2000-01-03', 'start': '08:00', 'end': '08:40', 'person_ids': ['T1'], 'campus_id': 'A'}]
        report = validate(data, refresh(data, solution))
        self.assertIn('EXTERNAL_CONFLICT', {v['code'] for v in report['hard_violations']})

    def test_calendar_exceptions_and_rotation(self):
        raw = examples()['training']
        raw['calendar']['exceptions'] = [{'date': '2026-11-07', 'open': False},
                                          {'date': '2026-11-09', 'open': True, 'schedule_weekday': 5}]
        days = expand_calendar(raw)
        self.assertNotIn('2026-11-07', {d['date'] for d in days})
        self.assertEqual(next(d for d in days if d['date'] == '2026-11-09')['weekday'], 5)
        data, solution, _ = copy.deepcopy(self.examples['junior'])
        for c in solution['assignments']:
            if c['demand_id'] == 'LAB1' and c['week_type'] == 'even':
                c['teacher_ids'] = ['T1']
        report = validate(data, refresh(data, solution))
        self.assertIn('TEACHER_ASSIGNMENT', {v['code'] for v in report['hard_violations']})

    def test_cancel_makeup_and_version(self):
        data, solution, _ = copy.deepcopy(self.examples['primary'])
        sid = solution['assignments'][0]['session_id']
        change = {'baseline_solution_hash': solution['solution_hash'], 'baseline_version': solution['version_hash'], 'operations': [{'action': 'cancel', 'session_id': sid}]}
        effective, canceled = adjust(data, solution, change)
        self.assertTrue(canceled['validation']['valid'])
        self.assertFalse(canceled['validation']['ready_for_acceptance'])
        original = next(c for c in solution['assignments'] if c['session_id'] == sid)
        makeup = dict(original, action='makeup', start=f'{original["start"]//60:02d}:{original["start"]%60:02d}')
        effective, result = adjust(effective, canceled, {'baseline_solution_hash': canceled['solution_hash'], 'baseline_version': canceled['version_hash'], 'operations': [makeup]})
        self.assertTrue(result['validation']['ready_for_acceptance'], result['validation']['hard_violations'])
        self.assertEqual(len(result['assignments']), len(solution['assignments']))
        with self.assertRaises(InputError):
            adjust(effective, result, change)

    def test_variable_length_cancel(self):
        data, solution, _ = copy.deepcopy(self.examples['training'])
        row = next(c for c in solution['assignments'] if c['end'] - c['start'] == 90)
        effective, result = adjust(data, solution, {'baseline_solution_hash': solution['solution_hash'], 'baseline_version': solution['version_hash'],
                    'operations': [{'action': 'cancel', 'session_id': row['session_id']}]})
        self.assertTrue(result['validation']['valid'], result['validation']['hard_violations'])

    def test_partial_coverage_blocks_final_export(self):
        data, solution, _ = copy.deepcopy(self.examples['primary'])
        data['external_scope_confirmed'] = False
        solution = refresh(data, solution)
        report = validate(data, solution)
        self.assertTrue(report['valid'])
        self.assertFalse(report['ready_for_acceptance'])
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(InputError):
                export(data, solution, report, Path(folder) / 'result.xlsx')
            path = export(data, solution, report, Path(folder) / 'result.xlsx', draft=True)
            self.assertIn('未通过校验', path)

    def test_duplicate_missing_and_malformed_assignments(self):
        for mode in ['duplicate', 'missing', 'malformed']:
            data, solution, _ = copy.deepcopy(self.examples['primary'])
            if mode == 'duplicate':
                solution['assignments'].append(copy.deepcopy(solution['assignments'][0]))
            elif mode == 'missing':
                solution['assignments'].pop()
            else:
                del solution['assignments'][0]['teacher_ids']
            self.assertFalse(validate(data, refresh(data, solution))['valid'])

    def test_excel_and_stale_report(self):
        data, solution, report = self.examples['primary']
        with tempfile.TemporaryDirectory(prefix='中文路径') as folder:
            path = export(data, solution, report, Path(folder) / '课表.xlsx')
            wb = load_workbook(path)
            self.assertTrue({'活动明细', '教学需求', '组课表', '教师课表', '校验结果'} <= set(wb.sheetnames))
            self.assertEqual(wb['教学需求']['E2'].data_type, 'f')
            self.assertEqual(wb['教学需求']['I2'].value, report['quota_deltas'][0]['actual_sessions'])
            with self.assertRaises(InputError):
                export(data, solution, dict(report, input_hash='stale'), path)

    def test_timeout_and_cli(self):
        data = normalize(tiny())
        result = solve(data, 0)
        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertFalse(validate(data, result)['valid'])
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            write_json(folder / 'input.json', data)
            args = [sys.executable, '-X', 'utf8', str(ROOT / 'scripts/cli.py')]
            run = subprocess.run(args + ['solve', '--input', str(folder / 'input.json'), '--output', str(folder / 'solution.json'), '--time-limit', '0'], capture_output=True)
            self.assertEqual(run.returncode, 4, run.stderr)
            self.assertEqual(json.loads((folder / 'solution.json').read_text(encoding='utf-8'))['status'], 'UNKNOWN')
            run = subprocess.run(args + ['solve', '--input', str(folder / 'input.json'), '--output', str(folder / 'input.json')], capture_output=True)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(json.loads((folder / 'input.json').read_text(encoding='utf-8')), data)

    def test_22class_capacity(self):
        data = normalize(grade22())
        solution = solve(data, 60)
        self.assertEqual(len(solution['assignments']), 990)
        self.assertTrue(validate(data, solution)['ready_for_acceptance'])

    def test_rule_layers_match_independent_metrics(self):
        # Every supported rule executes in both solver and independent validator.
        rules = [
            {'type': 'daily_limit', 'max': 1}, {'type': 'same_half_day'},
            {'type': 'consecutive', 'max_break_minutes': 15},
            {'type': 'daily_distribution', 'target': 2}, {'type': 'workdays', 'target': 2, 'by': 'teacher'},
            {'type': 'ampm_balance', 'by': 'teacher'},
            {'type': 'no_all_bad', 'slot_ids': ['P1'], 'by': 'teacher'},
            {'type': 'tail_excess', 'slot_ids': ['P1', 'P2'], 'max': 1, 'by': 'teacher'},
            {'type': 'preferred_time', 'windows': [{'start': '08:00', 'end': '08:40'}]},
            {'type': 'minimize_gaps', 'by': 'teacher'},
            {'type': 'synchronize', 'demand_ids': ['A', 'B']},
            {'type': 'precedence', 'demand_ids': ['A', 'B']},
            {'type': 'min_gap', 'minutes': 60},
        ]
        for index, rule in enumerate(rules):
            with self.subTest(rule=rule['type']):
                raw = tiny()
                raw['rules'] = [dict(rule, id='R', level='soft', tier=0)]
                data = normalize(raw)
                solution = solve(data, 10)
                report = validate(data, solution)
                self.assertTrue(report['valid'], report['hard_violations'])
                self.assertEqual(solution['layers'][0]['value'], report['rule_results'][0]['penalty'])

    def test_swap_lock_and_replan(self):
        raw = tiny()
        raw['demands'][0]['quota']['value'] = 1
        data = normalize(raw)
        solution = solve(data, 5)
        ids = [c['session_id'] for c in solution['assignments']]
        effective, result = adjust(data, solution, {'baseline_solution_hash': solution['solution_hash'],
            'baseline_version': solution['version_hash'], 'operations': [{'action': 'swap', 'session_ids': ids}]})
        self.assertTrue(result['validation']['valid'], result['validation']['hard_violations'])
        old = result['assignments'][0]
        effective, replanned = adjust(effective, result, {'baseline_solution_hash': result['solution_hash'],
            'baseline_version': result['version_hash'], 'operations': [
                {'action': 'lock', 'session_id': old['session_id'], 'fields': ['teacher_ids', 'date', 'start']},
                {'action': 'replan'}]})
        self.assertTrue(replanned['validation']['valid'], replanned['validation']['hard_violations'])
        row = next(c for c in replanned['assignments'] if c['session_id'] == old['session_id'])
        self.assertEqual(row['start'], old['start'])

    def test_hard_gap_and_priority_bottom_line(self):
        raw = tiny()
        raw['demands'] = [demand('A', 'G1', 'T1', count=1)]
        raw['rules'] = [
            {'id': 'bottom', 'type': 'no_all_bad', 'by': 'teacher', 'slot_ids': ['P1'], 'level': 'soft', 'tier': 0, 'weight': 1},
            {'id': 'prefer', 'type': 'preferred_time', 'windows': [{'start': '08:00', 'end': '08:40'}], 'level': 'soft', 'tier': 1, 'weight': 100}]
        data = normalize(raw)
        solution = solve(data, 5)
        self.assertEqual(solution['assignments'][0]['slot_id'], 'P2')
        self.assertEqual([l['value'] for l in solution['layers']], [0, 100])
        raw['demands'][0]['quota']['value'] = 2
        raw['rules'] = [{'id': 'min', 'type': 'min_gap', 'minutes': 60}]
        raw['calendar']['weekdays'] = [0]
        self.assertEqual(solve(normalize(raw), 5)['status'], 'INFEASIBLE')

    def test_qualification_seats_buffer_and_workload(self):
        for mode in ['qualification', 'seats', 'buffer', 'workload']:
            raw = tiny()
            raw['demands'] = [demand('A', 'G1', 'T1', count=1)]
            raw['calendar']['weekdays'] = [0]
            raw['slots'] = raw['slots'][:1]
            if mode == 'qualification':
                raw['demands'][0]['required_qualification'] = 'missing'
            elif mode == 'seats':
                raw['resources'][0]['seats'] = 1
            elif mode == 'buffer':
                raw['resources'][0]['availability'] = [{'start': '08:00', 'end': '08:40'}]
                raw['resources'][0]['setup_minutes'] = 10
            else:
                raw['teachers'][0]['daily_minutes'] = 30
            with self.subTest(mode=mode):
                self.assertEqual(solve(normalize(raw), 5)['status'], 'INFEASIBLE')

    def test_student_availability_and_split_parallel(self):
        raw = examples()['senior']
        raw['students'][0]['availability'] = []
        self.assertEqual(solve(normalize(raw), 5)['status'], 'INFEASIBLE')
        raw = examples()['senior']
        raw['demands'] = [dict(demand('A', 'G1', 'T1', count=1), fixed=[{'slot_id': 'P1', 'weekday': 0}]),
                          dict(demand('B', 'G3', 'T2', count=1), fixed=[{'slot_id': 'P1', 'weekday': 0}])]
        data = normalize(raw)
        self.assertTrue(validate(data, solve(data, 5))['ready_for_acceptance'])

    def test_changed_activity_status_and_rotation_missing_teacher(self):
        data, solution, _ = copy.deepcopy(self.examples['primary'])
        solution['assignments'][0]['status'] = 'finished'
        self.assertFalse(validate(data, refresh(data, solution))['valid'])
        raw = tiny()
        raw['demands'][0]['teacher_ids'] = []
        raw['demands'][0]['rotation'] = {'all': {'course_id': '课程'}}
        data = normalize(raw)
        solution = solve(data, 5)
        self.assertFalse(validate(data, solution)['ready_for_acceptance'])


if __name__ == '__main__':
    unittest.main()
