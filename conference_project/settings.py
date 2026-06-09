"""
Django settings for conference_project (ICRAET 2026 marksheet portal).

Local development:
  python manage.py runserver

PythonAnywhere / production:
  set DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, DJANGO_CSRF_TRUSTED_ORIGINS
  python manage.py migrate && python manage.py collectstatic --noinput
"""

import os
import socket
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv():
    """Load project .env into os.environ (does not override existing vars)."""
    env_path = BASE_DIR / '.env'
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()


def _env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in ('1', 'true', 'yes', 'on')


def _lan_ip():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(('8.8.8.8', 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return None


def _dev_server_ports():
    ports = os.environ.get('DJANGO_DEV_PORTS', '8000,8001,8080')
    return [p.strip() for p in ports.split(',') if p.strip()]


# DEBUG off by default on PythonAnywhere; on locally it defaults to True.
ON_PYTHONANYWHERE = bool(os.environ.get('PYTHONANYWHERE_DOMAIN'))
DEBUG = _env_bool('DJANGO_DEBUG', default=not ON_PYTHONANYWHERE)

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-txe$9#26r_ttf)!i=7b-47bve8=s%2-411*^q#k8xa#x*gg!pr'
    else:
        raise ImproperlyConfigured(
            'Set DJANGO_SECRET_KEY in the Web tab, or create a .env file in the '
            f'project root ({BASE_DIR / ".env"}). See .env.example.'
        )

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']
for host in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(','):
    host = host.strip()
    if host:
        ALLOWED_HOSTS.append(host)

_pa_domain = os.environ.get('PYTHONANYWHERE_DOMAIN')
if _pa_domain and _pa_domain not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_pa_domain)

if DEBUG and _env_bool('DJANGO_ALLOW_LAN', default=True):
    ALLOWED_HOSTS = ['*']
elif not DEBUG and not os.environ.get('DJANGO_ALLOWED_HOSTS') and not _pa_domain:
    ALLOWED_HOSTS.append('.pythonanywhere.com')
else:
    lan = _lan_ip()
    if lan and DEBUG:
        ALLOWED_HOSTS.append(lan)

CSRF_TRUSTED_ORIGINS = []
for origin in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(','):
    origin = origin.strip()
    if origin:
        CSRF_TRUSTED_ORIGINS.append(origin)

if _pa_domain:
    _pa_origin = f'https://{_pa_domain}'
    if _pa_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_pa_origin)

if DEBUG:
    for port in _dev_server_ports():
        CSRF_TRUSTED_ORIGINS.extend([
            f'http://localhost:{port}',
            f'http://127.0.0.1:{port}',
        ])
        lan = _lan_ip()
        if lan:
            CSRF_TRUSTED_ORIGINS.append(f'http://{lan}:{port}')
    CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(CSRF_TRUSTED_ORIGINS))

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'marksheet',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'conference_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'marksheet.context_processors.portal_roles',
            ],
        },
    },
]

WSGI_APPLICATION = 'conference_project.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

FACULTY_DATA_FILE = Path(
    os.environ.get('FACULTY_DATA_FILE', str(BASE_DIR / 'fac data.xlsx'))
)
DEFAULT_EVALUATION_TEMPLATE = Path(
    os.environ.get(
        'DEFAULT_EVALUATION_TEMPLATE',
        str(BASE_DIR / 'marksheet' / 'data' / 'evaluation_form_template.xlsx'),
    )
)

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

FILE_UPLOAD_MAX_MEMORY_SIZE = 15 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 15 * 1024 * 1024

MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    CSRF_COOKIE_SECURE = _env_bool('DJANGO_CSRF_COOKIE_SECURE', default=True)
    SESSION_COOKIE_SECURE = _env_bool('DJANGO_SESSION_COOKIE_SECURE', default=True)
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
