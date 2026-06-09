"""Send colorful HTML credential emails (once per person)."""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def validate_email_config():
    backend = settings.EMAIL_BACKEND or ''
    if 'console' in backend:
        return (
            False,
            'Emails are NOT sent — console backend is active. '
            'Set DJANGO_EMAIL_BACKEND=smtp and Gmail credentials in .env '
            '(local) or Web → Environment variables (PythonAnywhere).',
        )
    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        return (
            False,
            'Gmail not configured. Set DJANGO_EMAIL_HOST_USER and '
            'DJANGO_EMAIL_HOST_PASSWORD in .env or PythonAnywhere environment variables.',
        )
    try:
        connection = get_connection(
            fail_silently=False,
            timeout=20,
        )
        connection.open()
        connection.close()
    except Exception as exc:
        msg = str(exc)
        if '535' in msg or 'BadCredentials' in msg or 'Username and Password not accepted' in msg:
            return (
                False,
                'Gmail login failed — app password is wrong or expired. '
                'Create a new App Password at https://myaccount.google.com/apppasswords '
                'and update DJANGO_EMAIL_HOST_PASSWORD (no spaces).',
            )
        if '101' in msg or 'Network is unreachable' in msg:
            return (
                False,
                'Cannot reach Gmail SMTP from this server. On PythonAnywhere free accounts, '
                'only Gmail SMTP is allowed — ensure env vars are set and reload the web app.',
            )
        return False, f'Email server connection failed: {msg}'
    return True, ''


def _from_email():
    user = settings.EMAIL_HOST_USER
    default = settings.DEFAULT_FROM_EMAIL
    if user and user in (default or ''):
        return user
    if user and '@' in user and '<' not in (default or ''):
        return f'ICRAET 2026 <{user}>'
    return default or user


def send_credential_emails(recipients, login_url):
    ok, config_error = validate_email_config()
    if not ok:
        return {
            'sent': 0,
            'skipped_no_email': 0,
            'skipped_duplicate': 0,
            'failed': [],
            'config_error': config_error,
        }

    seen_ids = set()
    sent = 0
    skipped_no_email = 0
    skipped_duplicate = 0
    failed = []
    from_email = _from_email()
    connection = get_connection(fail_silently=False, timeout=30)

    for person in recipients:
        pid = person.get('profile_id')
        if pid in seen_ids:
            skipped_duplicate += 1
            continue
        seen_ids.add(pid)

        email = (person.get('email') or '').strip()
        if not email:
            skipped_no_email += 1
            continue

        try:
            html = render_to_string('marksheet/emails/credential_email.html', {
                'person': person,
                'login_url': login_url,
                'site_name': 'ICRAET 2026',
                'org_name': 'LJIET — Lok Jagruti University',
            })
            subject = (
                f"ICRAET 2026 — Your {person.get('role_label', 'Portal')} Login Credentials"
            )
            plain = (
                f"Dear {person.get('name', '')},\n\n"
                f"Login: {person.get('username', '')}\n"
                f"Password: {person.get('password', '')}\n"
                f"Portal: {login_url}\n"
            )
            message = EmailMultiAlternatives(
                subject=subject,
                body=plain,
                from_email=from_email,
                to=[email],
                connection=connection,
            )
            message.attach_alternative(html, 'text/html')
            message.send(fail_silently=False)
            sent += 1
            logger.info('Credential email sent to %s (%s)', person.get('name'), email)
        except Exception as exc:
            logger.exception('Failed to send credential email to %s', email)
            failed.append({
                'name': person.get('name', ''),
                'email': email,
                'error': str(exc),
            })

    try:
        connection.close()
    except Exception:
        pass

    return {
        'sent': sent,
        'skipped_no_email': skipped_no_email,
        'skipped_duplicate': skipped_duplicate,
        'failed': failed,
        'config_error': '',
    }
