from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import date, datetime
from pathlib import Path

VERSION = '1.0.3'
ROOT = Path(__file__).resolve().parents[1]


class InputError(ValueError):
    def __init__(self, message, path='input', code='INVALID_INPUT'):
        super().__init__(message)
        self.path, self.code = path, code


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_json(path, value):
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def atomic_text(path, text):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def minute(value):
    try:
        h, m = map(int, value.split(':'))
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError()
        return h * 60 + m
    except (ValueError, AttributeError):
        raise InputError(f'非法时间 {value!r}，要求 HH:MM')


def clock(value):
    return f'{value // 60:02d}:{value % 60:02d}'


def stamp():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def overlap(a, b):
    return a['date'] == b['date'] and a['start'] < b['end'] and b['start'] < a['end']


def entries(items, key):
    result = {}
    for i, item in enumerate(items):
        identity = item.get(key)
        if not isinstance(identity, str) or not identity:
            raise InputError(f'缺少 {key}', f'{key}[{i}]')
        if identity in result:
            raise InputError(f'重复标识 {identity}', f'{key}[{i}]', 'DUPLICATE_ID')
        result[identity] = item
    return result


def integer(value, path, minimum=0):
    if type(value) is not int or value < minimum:
        raise InputError(f'{path} 必须是 >= {minimum} 的整数', path)
    return value


def is_date(value):
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        raise InputError(f'非法日期 {value!r}')
