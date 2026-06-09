#!/bin/bash
# Run after every git pull on PythonAnywhere to avoid 500 errors.
# Usage: bash deploy/post_update.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

if [ ! -f ".env" ]; then
    echo "ERROR: Missing .env file. Run: bash deploy/pythonanywhere_setup.sh"
    exit 1
fi

if ! grep -q '^DJANGO_SECRET_KEY=.' .env 2>/dev/null; then
    echo "ERROR: DJANGO_SECRET_KEY is missing in .env"
    echo "  Generate one: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\""
    exit 1
fi

source .venv/bin/activate

echo "==> Installing dependencies..."
pip install -r requirements.txt

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo ""
echo "Done. Now click Reload on the PythonAnywhere Web tab."
