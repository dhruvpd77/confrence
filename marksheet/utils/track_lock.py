from django.utils import timezone

from marksheet.models import TrackSessionLock


def get_track_lock(schedule, day, track_session):
    lock, _ = TrackSessionLock.objects.get_or_create(
        schedule=schedule,
        day=day,
        track_session=track_session,
        defaults={'is_locked': False},
    )
    return lock


def is_track_locked(schedule, day, track_session):
    if not schedule:
        return False
    return TrackSessionLock.objects.filter(
        schedule=schedule,
        day=day,
        track_session=track_session,
        is_locked=True,
    ).exists()


def lock_track(schedule, day, track_session, user):
    lock = get_track_lock(schedule, day, track_session)
    lock.is_locked = True
    lock.locked_at = timezone.now()
    lock.locked_by = user
    lock.save()
    return lock


def get_locks_map(schedule, day=None):
    locks = TrackSessionLock.objects.filter(schedule=schedule, is_locked=True)
    if day:
        locks = locks.filter(day=day)
    return {(lk.day, lk.track_session): lk for lk in locks}
