"""Run anonymous local acceptance samples; output must be outside the release assets."""
import argparse
import ctypes
import platform
import sys
import time
from importlib.metadata import version
from pathlib import Path
from common import ROOT, read_json, write_json, stamp, digest
from normalize_input import normalize
from cp_sat_scheduler import solve
from validate_schedule import validate
from excel_io import export


def peak_memory_mb():
    if sys.platform != 'win32':
        return None
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [(name, ctypes.c_size_t) for name in
                    ['PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage',
                     'QuotaPeakNonPagedPoolUsage', 'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage']]
    mem = Counters()
    mem.cb = ctypes.sizeof(mem)
    kernel = ctypes.WinDLL('kernel32')
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    process = kernel.GetCurrentProcess()
    api = ctypes.WinDLL('psapi').GetProcessMemoryInfo
    api.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    if api(process, ctypes.byref(mem), mem.cb):
        return round(mem.PeakWorkingSetSize / 1024**2, 1)
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True)
    args = p.parse_args()
    target = Path(args.output).resolve()
    if ROOT == target or ROOT in target.parents:
        raise ValueError('基准产物必须放技能包目录之外')
    report = {'generated_at': stamp(), 'python': sys.version, 'platform': platform.platform(),
              'ortools': version('ortools'), 'openpyxl': version('openpyxl'), 'samples': [],
              'limits': ['均为脱敏样例，不代表真实学校验收', '22班样本时间已固定，仅容量基准',
                         '内存为当前进程累计峰值，不是单样例增量', 'WorkBuddy实际调用和Excel/WPS重算未验证']}
    for name in ['primary', 'junior', 'senior', 'training', 'senior-22classes-synthetic']:
        data = normalize(read_json(ROOT / 'assets' / (name + '.json')))
        start = time.monotonic()
        solution = solve(data, 120)
        report_start = time.monotonic()
        validation = validate(data, solution)
        folder = target / name
        write_json(folder / 'input.json', data)
        write_json(folder / 'solution.json', solution)
        write_json(folder / 'validation.json', validation)
        if not validation['ready_for_acceptance']:
            raise RuntimeError(f'{name}验收失败: {validation["hard_violations"]}')
        output = export(data, solution, validation, folder / '课表.xlsx')
        report['samples'].append({'profile': name, 'status': solution['status'],
                                  'activities': len(solution['assignments']), 'groups': len(data['groups']),
                                  'teachers': len(data['teachers']), 'resources': len(data['resources']),
                                  'calendar_days': len(data['expanded_calendar']),
                                  'candidates': solution['candidate_count'], 'solver_seconds': solution['elapsed_seconds'],
                                  'validation_export_seconds': round(time.monotonic()-report_start, 3),
                                  'total_seconds': round(time.monotonic()-start, 3), 'peak_process_mb': peak_memory_mb(),
                                  'ready_for_acceptance': True, 'input_hash': digest(data), 'output': output})
        print(name, report['samples'][-1], flush=True)
    write_json(target / 'benchmark.json', report)


if __name__ == '__main__':
    main()
