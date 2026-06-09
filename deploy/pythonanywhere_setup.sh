#!/bin/bash
# Run once in a PythonAnywhere Bash console after cloning the repo.
# Usage: bash deploy/pythonanywhere_setup.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "==> Project: $PROJECT_DIR"

if [ ! -d ".venv" ]; then
    echo "==> Creating virtualenv..."
    python3.10 -m venv .venv || python3.11 -m venv .venv
fi

source .venv/bin/activate

echo "==> Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f ".env" ]; then
    echo "==> Creating .env from .env.example (edit DJANGO_SECRET_KEY before going live)..."
    cp .env.example .env
    SECRET=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
    sed -i "s/replace-with-a-long-random-string/$SECRET/" .env
fi

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

if [ ! -f "db.sqlite3" ]; then
    echo "==> Creating super admin (default: admin / admin123 — change after login)..."
    python manage.py create_superadmin
fi

mkdir -p media/schedules media/templates

echo ""
echo "Done. Next steps:"
echo "  1. Web tab → set virtualenv to: $PROJECT_DIR/.venv"
echo "  2. Web tab → WSGI file → use deploy/pythonanywhere_wsgi.py (edit YOURUSERNAME)"
echo "  3. Web tab → Environment variables → copy from .env.example"
echo "  4. Web tab → Static files → /media/ → $PROJECT_DIR/media"
echo "  5. Reload web app"
