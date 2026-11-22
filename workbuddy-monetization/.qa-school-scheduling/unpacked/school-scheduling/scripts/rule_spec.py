from datetime import date
from common import minute
from expand_calendar import window_applies


def selected(rule, c):
    return (('demand_ids' not in rule or c['demand_id'] in rule['demand_ids']) and
            ('teacher_ids' not in rule or bool(set(c['teacher_ids']) & set(rule['teacher_ids']))) and
            ('group_ids' not in rule or bool(set(c['group_ids']) & set(rule['group_ids']))) and
            ('course_ids' not in rule or c['course_id'] in rule['course_ids']))


def entities(rule, c):
    by = rule.get('by', 'demand')
    if by == 'teacher':
        return [t for t in c['teacher_ids'] if 'teacher_ids' not in rule or t in rule['teacher_ids']]
    if by == 'group':
        return [g for g in c['group_ids'] if 'group_ids' not in rule or g in rule['group_ids']]
    return [c['demand_id']]


def preferred(rule, c):
    return any(window_applies(w, c) and minute(w['start']) <= c['start'] and c['end'] <= minute(w['end'])
               for w in rule['windows'])


def bad(rule, c):
    return c['slot_id'] in rule.get('slot_ids', []) or any(
        window_applies(w, c) and c['start'] < minute(w['end']) and minute(w['start']) < c['end']
        for w in rule.get('windows', []))


def absolute(c):
    return date.fromisoformat(c['date']).toordinal() * 1440 + c['start']
