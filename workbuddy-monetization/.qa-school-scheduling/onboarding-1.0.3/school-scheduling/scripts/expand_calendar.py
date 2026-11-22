from datetime import date, timedelta
from common import InputError, is_date, minute


def expand_calendar(data):
    cal = data['calendar']
    types = cal.get('week_types', ['all'])
    if not types or len(set(types)) != len(types):
        raise InputError('week_types 不能为空或重复', 'calendar.week_types')
    if data['mode'] == 'weekly_template':
        start = date(2000, 1, 3)
        finish = start + timedelta(days=7 * len(types) - 1)
        anchor = start
    else:
        start, finish = is_date(cal['start_date']), is_date(cal['end_date'])
        anchor = is_date(cal.get('week_anchor', cal['start_date']))
        if anchor.weekday() != 0:
            raise InputError('week_anchor 必须为周一，以定义周型起点', 'calendar.week_anchor')
    if finish < start or (finish - start).days > 730:
        raise InputError('日期范围无效，单任务最多覆盖731天', 'calendar')
    weekdays = cal.get('weekdays', [0, 1, 2, 3, 4])
    if any(type(d) is not int or d not in range(7) for d in weekdays):
        raise InputError('weekdays 使用0至6，0为周一', 'calendar.weekdays')
    exceptions = {}
    for ex in cal.get('exceptions', []):
        day = is_date(ex['date']).isoformat()
        if day in exceptions:
            raise InputError('同日重复日历例外', 'calendar.exceptions')
        exceptions[day] = ex
    result = []
    day = start
    while day <= finish:
        text = day.isoformat()
        ex = exceptions.get(text, {})
        wd = ex.get('schedule_weekday', day.weekday())
        wt = ex.get('week_type', types[((day - anchor).days // 7) % len(types)])
        if wt not in types or wd not in range(7):
            raise InputError('日历例外的星期或周型不合法', 'calendar.exceptions')
        opened = ex.get('open', day.weekday() in weekdays and text not in cal.get('holidays', []))
        if opened:
            result.append({'date': text, 'weekday': wd, 'actual_weekday': day.weekday(),
                           'week_type': wt, 'cycle': (day - timedelta(days=day.weekday())).isoformat()})
        day += timedelta(days=1)
    if not result:
        raise InputError('排课范围内无教学日', 'calendar')
    return result


def window_applies(window, day):
    return (('dates' not in window or day['date'] in window['dates']) and
            ('weekdays' not in window or day['weekday'] in window['weekdays']) and
            ('week_types' not in window or day['week_type'] in window['week_types']))


def available(person, when, day):
    # Missing windows means unknown, not complete coverage; validation reports it.
    allowed = person.get('availability')
    denied = person.get('unavailability', [])
    inside = allowed is None or any(window_applies(w, day) and
                                    minute(w['start']) <= when['start'] and when['end'] <= minute(w['end'])
                                    for w in allowed)
    return inside and not any(window_applies(w, day) and when['start'] < minute(w['end'])
                              and minute(w['start']) < when['end'] for w in denied)
