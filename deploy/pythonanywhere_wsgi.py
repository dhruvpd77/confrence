"""
PythonAnywhere WSGI entry point.

1. Upload/clone the project to e.g. /home/YOURUSERNAME/coNFRENCE
2. Open the Web tab → your site → WSGI configuration file
3. Replace its contents with this file (update YOURUSERNAME and paths)
4. Reload the web app
"""

import os
import sys

# Project folder on PythonAnywhere (username: ljietConference7)
PROJECT_HOME = '/home/ljietConference7/coNFRENCE'

if PROJECT_HOME not in sys.path:
    sys.path.insert(0, PROJECT_HOME)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conference_project.settings')

# Set in Web → Environment variables (recommended) or uncomment below:
# os.environ['DJANGO_SECRET_KEY'] = 'your-secret-key'
# os.environ['DJANGO_DEBUG'] = '0'
# os.environ['DJANGO_ALLOWED_HOSTS'] = 'yourusername.pythonanywhere.com'
# os.environ['DJANGO_CSRF_TRUSTED_ORIGINS'] = 'https://yourusername.pythonanywhere.com'

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
