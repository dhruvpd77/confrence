"""Build credential rows and email recipient groups for Moderator-2 and Verifier."""

from marksheet.utils.faculty_credentials import (
    MODERATOR_2_LABEL,
    get_faculty_duties,
    get_moderator2_profiles,
)
from marksheet.utils.faculty_matcher import FacultyMatcher
from marksheet.utils.verifier_credentials import get_verifier_duties, get_verifier_profiles


def resolve_profile_contact(profile, matcher=None):
    """Saved profile contact overrides fac data.xlsx lookup."""
    matcher = matcher or FacultyMatcher()
    phone = (profile.phone or '').strip()
    email = (getattr(profile, 'email', '') or '').strip()
    if not phone:
        phone = matcher.find_mobile(profile.display_name) or ''
    if not email:
        email = matcher.find_email(profile.display_name) or ''
    return phone, email


def _contact_for_name(matcher, display_name, stored_phone='', stored_email=''):
    phone = (stored_phone or '').strip()
    email = (stored_email or '').strip()
    if not phone or not email:
        contact = matcher.find_contact(display_name)
        if not phone:
            phone = contact['phone'] or ''
        if not email:
            email = contact['email'] or ''
    return phone, email


def build_credential_people(profiles):
    matcher = FacultyMatcher()
    people = []
    for profile in profiles:
        phone, email = resolve_profile_contact(profile, matcher)
        people.append({
            'profile_id': profile.id,
            'name': profile.display_name,
            'username': profile.user.username,
            'phone': phone,
            'email': email,
        })
    return people


def _duty_row(duty):
    return {
        'day': f'Day {duty.day}',
        'day_num': duty.day,
        'track_session': duty.track_session,
        'track_name': duty.track_name or duty.track_session,
        'room': duty.room,
    }


def build_moderator_credential_rows(schedule):
    matcher = FacultyMatcher()
    rows = []
    for profile in get_moderator2_profiles(schedule):
        phone, email = resolve_profile_contact(profile, matcher)
        duties = get_faculty_duties(profile, schedule=schedule)
        base = {
            'profile_id': profile.id,
            'name': profile.display_name,
            'username': profile.user.username,
            'password': profile.plain_password,
            'phone': phone,
            'email': email,
            'role': MODERATOR_2_LABEL,
        }
        if not duties:
            rows.append({**base, 'day': '—', 'track_session': '—', 'room': '—'})
            continue
        for item in duties:
            duty = item['duty']
            rows.append({**base, **_duty_row(duty)})
    return rows


def build_verifier_credential_rows(schedule):
    matcher = FacultyMatcher()
    rows = []
    for profile in get_verifier_profiles(schedule):
        phone, email = resolve_profile_contact(profile, matcher)
        duties = get_verifier_duties(profile, schedule=schedule)
        base = {
            'profile_id': profile.id,
            'name': profile.display_name,
            'username': profile.user.username,
            'password': profile.plain_password,
            'phone': phone,
            'email': email,
            'role': 'Verifier',
        }
        if not duties:
            rows.append({**base, 'day': '—', 'track_session': '—', 'room': '—'})
            continue
        for item in duties:
            duty = item['duty']
            rows.append({**base, **_duty_row(duty)})
    return rows


def group_moderator_email_recipients(schedule):
    """One email per Moderator-2 profile (multiple track rows → single mail)."""
    matcher = FacultyMatcher()
    recipients = []
    for profile in get_moderator2_profiles(schedule):
        phone, email = resolve_profile_contact(profile, matcher)
        duty_rows = []
        for item in get_faculty_duties(profile, schedule=schedule):
            duty_rows.append(_duty_row(item['duty']))
        recipients.append({
            'profile_id': profile.id,
            'name': profile.display_name,
            'username': profile.user.username,
            'password': profile.plain_password,
            'phone': phone,
            'email': email,
            'role_label': 'Moderator-2 (Entry)',
            'duties': duty_rows,
        })
    return recipients


def group_verifier_email_recipients(schedule):
    recipients = []
    matcher = FacultyMatcher()
    for profile in get_verifier_profiles(schedule):
        phone, email = resolve_profile_contact(profile, matcher)
        duty_rows = []
        for item in get_verifier_duties(profile, schedule=schedule):
            duty_rows.append(_duty_row(item['duty']))
        recipients.append({
            'profile_id': profile.id,
            'name': profile.display_name,
            'username': profile.user.username,
            'password': profile.plain_password,
            'phone': phone,
            'email': email,
            'role_label': 'Verifier',
            'duties': duty_rows,
        })
    return recipients


def credential_stats(rows):
    unique_people = len({r['profile_id'] for r in rows})
    with_email = len({r['profile_id'] for r in rows if r.get('email')})
    return {
        'total_rows': len(rows),
        'unique_people': unique_people,
        'with_email': with_email,
        'without_email': unique_people - with_email,
    }
