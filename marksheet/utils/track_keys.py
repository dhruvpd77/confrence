"""Track filter keys — distinguish poster groups that share the same track_session."""


def make_track_key(day, track_session, track_name=''):
    """Build a track filter key; include track_name when set (poster groups)."""
    if track_name:
        return f'{day}|{track_session}|{track_name}'
    return f'{day}|{track_session}'


def parse_track_key(track_key):
    """Return (day, track_session, track_name) — track_name is None when not in key."""
    if not track_key or '|' not in track_key:
        return None, None, None
    parts = track_key.split('|')
    try:
        day = int(parts[0])
    except (ValueError, IndexError):
        return None, None, None
    if len(parts) == 2:
        return day, parts[1], None
    track_session = parts[1]
    track_name = '|'.join(parts[2:])
    return day, track_session, track_name or None


def apply_track_key_filter(qs, track_key):
    day, track_session, track_name = parse_track_key(track_key)
    if day is None or not track_session:
        return qs
    qs = qs.filter(day=day, track_session=track_session)
    if track_name:
        qs = qs.filter(track_name=track_name)
    return qs


def duty_track_key(duty):
    return make_track_key(duty.day, duty.track_session, duty.track_name or '')


def paper_track_key(paper):
    return make_track_key(paper.day, paper.track_session, paper.track_name or '')


def papers_for_duty(qs, duty):
    """Papers belonging to a specific track duty (poster room / track name)."""
    filters = {'day': duty.day, 'track_session': duty.track_session}
    if duty.track_name:
        filters['track_name'] = duty.track_name
    return qs.filter(**filters)
