"""Track filter keys — distinguish poster groups that share the same track_session."""

from marksheet.utils.excel_parser import normalize_poster_room, poster_display_name


def make_track_key(day, track_session, track_name=''):
    """Build a track filter key; include track_name when it identifies a poster group."""
    track_name = (track_name or '').strip()
    if track_name and track_name != track_session:
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


def _claimed_poster_rooms(schedule, day, track_session, exclude_pk=None):
    """Rooms already assigned to other poster duties on the same day."""
    from marksheet.models import TrackDuty

    claimed = set()
    qs = TrackDuty.objects.filter(schedule=schedule, day=day, track_session=track_session)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    for other in qs:
        if other.room:
            claimed.add(normalize_poster_room(other.room))
        elif other.track_name and '|' in other.track_name:
            claimed.add(normalize_poster_room(other.track_name.split('|', 1)[0]))
    return claimed


def _resolve_poster_duty_room(duty):
    """Resolve poster venue from duty row or unclaimed paper groups on the same day."""
    from marksheet.models import Paper, TrackDuty

    room = normalize_poster_room(duty.room) if duty.room else ''
    if room:
        return room

    if duty.track_name and '|' in duty.track_name:
        room = normalize_poster_room(duty.track_name.split('|', 1)[0])
        if room:
            return room

    if duty.track_name and duty.track_name != duty.track_session:
        room = normalize_poster_room(duty.track_name)
        if room:
            return room

    if duty.moderator_2:
        sibling = (
            TrackDuty.objects.filter(
                schedule=duty.schedule,
                day=duty.day,
                moderator_2=duty.moderator_2,
            )
            .exclude(room='')
            .exclude(pk=duty.pk)
            .first()
        )
        if sibling and sibling.room:
            return normalize_poster_room(sibling.room)

    claimed = _claimed_poster_rooms(
        duty.schedule, duty.day, duty.track_session, exclude_pk=duty.pk
    )
    paper_rooms = {
        normalize_poster_room(r)
        for r in Paper.objects.filter(
            schedule=duty.schedule,
            day=duty.day,
            track_session=duty.track_session,
        ).values_list('room', flat=True)
        if r
    }
    unclaimed = sorted(room for room in paper_rooms if room and room not in claimed)
    if len(unclaimed) == 1:
        return unclaimed[0]

    return ''


def _repair_poster_duty(duty, room):
    """Persist corrected poster room/name on TrackDuty when we infer the venue."""
    from marksheet.models import TrackDuty

    expected_name = poster_display_name(room, duty.track_session)
    if duty.room == room and duty.track_name == expected_name:
        return
    TrackDuty.objects.filter(pk=duty.pk).update(room=room, track_name=expected_name)
    duty.room = room
    duty.track_name = expected_name


def papers_for_duty(qs, duty):
    """Papers belonging to a specific track duty (poster room / track name)."""
    base = qs.filter(day=duty.day, track_session=duty.track_session)

    if duty.track_name and duty.track_name != duty.track_session:
        match = base.filter(track_name=duty.track_name)
        if match.exists():
            return match

    if 'POSTER' in (duty.track_session or '').upper():
        room = _resolve_poster_duty_room(duty)
        if room:
            match = base.filter(room=room)
            if not match.exists():
                expected_name = poster_display_name(room, duty.track_session)
                match = base.filter(track_name=expected_name)
            if match.exists():
                _repair_poster_duty(duty, room)
                return match

    if duty.room:
        match = base.filter(room=duty.room)
        if match.exists():
            return match

    if duty.track_name:
        return base.filter(track_name=duty.track_name)
    return base
