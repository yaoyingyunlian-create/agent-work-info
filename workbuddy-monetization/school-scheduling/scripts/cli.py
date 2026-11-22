from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from common import ROOT, InputError, read_json, write_json, digest, VERSION


def parser():
    p = argparse.ArgumentParser(description='WorkBuddy 学校与培训机构排课')
    p.add_argument('--version', action='version', version=VERSION)
    sub = p.add_subparsers(dest='command', required=True)
    g = sub.add_parser('guide', help='首次使用与缺失资料引导，无需安装求解依赖')
    g.add_argument('--input', help='可选：已有资料与回答组成的部分JSON')
    g.add_argument('--output', help='可选：引导结果保存路径，不提供则只输出')
    t = sub.add_parser('template')
    t.add_argument('--profile', choices=['primary', 'junior', 'senior', 'training'], required=True)
    t.add_argument('--output', required=True)
    for command in ['import', 'precheck', 'solve', 'validate', 'adjust', 'export']:
        s = sub.add_parser(command)
        s.add_argument('--input', required=True)
        if command in ['validate', 'adjust', 'export']:
            s.add_argument('--solution', required=True)
        s.add_argument('--output' if command in ['import', 'solve', 'adjust', 'export'] else '--report', required=True)
        if command == 'solve':
            s.add_argument('--time-limit', type=float, default=120)
            s.add_argument('--workers', type=int, default=1)
            s.add_argument('--seed', type=int, default=0)
        if command == 'adjust':
            s.add_argument('--changes', required=True)
        if command == 'export':
            s.add_argument('--validation', required=True)
            s.add_argument('--draft', action='store_true')
    return p


def main(argv=None):
    actual = sys.argv[1:] if argv is None else argv
    args = parser().parse_args(actual or ['guide'])
    command = args.command
    try:
        destination = getattr(args, 'output', getattr(args, 'report', None))
        for name in ['input', 'solution', 'changes', 'validation']:
            source = getattr(args, name, None)
            if source and destination and Path(source).resolve() == Path(destination).resolve():
                raise InputError('输出路径不能覆盖输入、基线或校验文件，请使用新版本路径', name)
        if command == 'guide':
            from onboarding import guide
            result = guide(read_json(args.input) if args.input else None)
            if args.output:
                write_json(args.output, result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        from normalize_input import normalize
        if command == 'template':
            from excel_io import template
            template(read_json(ROOT / 'assets' / (args.profile + '.json')), args.output)
            print(json.dumps({'output': str(Path(args.output).resolve())}, ensure_ascii=False))
            return 0
        if command == 'import':
            from excel_io import import_excel
            data, errors = import_excel(args.input)
            if errors:
                write_json(str(args.output) + '.errors.json', {'errors': errors})
                print(json.dumps({'errors': errors}, ensure_ascii=False), file=sys.stderr)
                return 2
            write_json(args.output, data)
            return 0
        data = normalize(read_json(args.input))
        if command == 'precheck':
            from precheck import precheck
            report = precheck(data)
            write_json(args.report, report)
            return 0 if report['valid'] else 2
        if command == 'solve':
            from cp_sat_scheduler import solve
            from validate_schedule import validate
            if args.workers < 1 or args.time_limit < 0:
                raise InputError('workers必须≥1，time-limit必须≥0')
            from onboarding import guide
            write_json(str(args.output) + '.guidance.json', guide(dict(data, goal='new')))
            result = solve(data, args.time_limit, args.workers, args.seed)
            write_json(args.output, result)
            write_json(str(args.output) + '.input.json', data)
            code = {'INFEASIBLE': 3, 'UNKNOWN': 4, 'MODEL_INVALID': 2}.get(result['status'], 0)
            if result['assignments']:
                report = validate(data, result)
                write_json(str(args.output) + '.validation.json', report)
                if not report['valid'] or not report['quality']['gate_passed']:
                    return 5
            print(json.dumps({k: result.get(k) for k in ['status', 'candidate_count', 'elapsed_seconds', 'diagnostics']}, ensure_ascii=False))
            return code
        from validate_schedule import validate
        solution = read_json(args.solution)
        if command == 'validate':
            report = validate(data, solution)
            write_json(args.report, report)
            print(json.dumps({'valid': report['valid'], 'ready_for_acceptance': report['ready_for_acceptance']}, ensure_ascii=False))
            return 0 if report['valid'] and report['quality']['gate_passed'] else 5
        if command == 'adjust':
            from adjust_schedule import adjust
            effective, result = adjust(data, solution, read_json(args.changes))
            write_json(args.output, result)
            write_json(str(args.output) + '.input.json', effective)
            write_json(str(args.output) + '.validation.json', result['validation'])
            return 0 if result['validation']['valid'] and result['validation']['quality']['gate_passed'] else 5
        if command == 'export':
            from excel_io import export
            actual = export(data, solution, read_json(args.validation), args.output, args.draft)
            manifest = {'version': VERSION, 'input_hash': digest(data), 'solution_hash': solution['solution_hash'],
                        'output': actual, 'file_sha256': __import__('hashlib').sha256(Path(actual).read_bytes()).hexdigest(),
                        'parameters': solution.get('parameters'), 'layers': solution.get('layers'),
                        'delivery_status': validate(data, solution)['delivery_status']}
            write_json(actual + '.manifest.json', manifest)
            print(json.dumps(manifest, ensure_ascii=False))
            return 0
    except (InputError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({'error_code': getattr(exc, 'code', 'INVALID_INPUT'), 'path': getattr(exc, 'path', 'input'), 'message': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    except ImportError as exc:
        print(f'依赖缺失: {exc}。请运行技能包 scripts/setup.ps1。', file=sys.stderr)
        return 1
    except Exception as exc:
        print(f'运行异常 {type(exc).__name__}: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
