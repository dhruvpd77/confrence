# ICRAET 2026 — Conference Marksheet Management System

Django web application for uploading conference schedule Excel files and generating track-wise evaluation marksheets.

## Features

- **Super Admin Login** — Secure authentication for super admin only
- **Schedule Upload** — Upload `FINAL_TRACK WISE_DISTRIBUTION` Excel file with Day 1 & Day 2 sheets
- **Marksheet Template Upload** — Upload your custom `EVALUATION FORM` Excel template; all formatting, borders, colors, and max marks are preserved
- **Auto Parse** — Extracts Paper ID, Paper Title, Author Name, Track/Session, Session Chair
- **Track-wise Download** — Select track from dropdown → Excel with multiple sheets (one per paper, serial number wise)
- **Day-wise Download** — Download all tracks for Day 1 or Day 2
- **Download All** — Complete marksheets for all days and tracks

## Local setup

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py create_superadmin
set DJANGO_DEBUG=1
python manage.py runserver
```

On Windows PowerShell use `$env:DJANGO_DEBUG=1` instead of `set`.

## Deploy on PythonAnywhere

### 1. Upload code

Clone or upload this project to e.g. `/home/YOURUSERNAME/coNFRENCE` (GitHub, Files tab, or `git clone`).

Include these files in the upload:

- `fac data.xlsx` (faculty mobile lookup)
- `EVALUATION FORM (1).xlsx` (optional default marksheet template — or upload via admin UI later)

### 2. One-time setup (Bash console)

```bash
cd ~/coNFRENCE
bash deploy/pythonanywhere_setup.sh
```

### 3. Web app configuration

| Setting | Value |
|--------|--------|
| **Source code** | `/home/YOURUSERNAME/coNFRENCE` |
| **Virtualenv** | `/home/YOURUSERNAME/coNFRENCE/.venv` |
| **WSGI file** | Copy from `deploy/pythonanywhere_wsgi.py` (replace `YOURUSERNAME`) |

**Environment variables** (Web tab → Environment variables — see `.env.example`):

```
DJANGO_SECRET_KEY=<random-string>
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=yourusername.pythonanywhere.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://yourusername.pythonanywhere.com
```

Generate a secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**Static / media** (Web tab → Static files):

| URL | Directory |
|-----|-----------|
| `/media/` | `/home/YOURUSERNAME/coNFRENCE/media` |

CSS/JS are served via WhiteNoise after `collectstatic` (no extra static mapping needed).

### 4. Reload

Click **Reload** on the Web tab, then open `https://yourusername.pythonanywhere.com/`.

### 5. After deploy

1. Login as `admin` and change the password immediately.
2. Upload the schedule Excel from the admin dashboard.
3. Upload marksheet template if you did not bundle `EVALUATION FORM (1).xlsx`.

### Updates

```bash
cd ~/coNFRENCE
git pull
bash deploy/post_update.sh
```

Then **Reload** the web app on the Web tab.

### Fix "Server Error (500)" after git pull

1. **Bash console** — run `bash deploy/post_update.sh` (migrates DB + collects static files).
2. **Check `.env`** exists in `~/coNFRENCE/` with `DJANGO_SECRET_KEY` set (copy from `.env.example` if missing).
3. **Web tab → WSGI** — ensure `PROJECT_HOME` is `/home/ljietConference7/coNFRENCE` (see `deploy/pythonanywhere_wsgi.py`).
4. **Web tab → Environment variables** — set at minimum:
   - `DJANGO_SECRET_KEY`
   - `DJANGO_DEBUG=0`
   - `DJANGO_ALLOWED_HOSTS=ljietconference7.pythonanywhere.com`
   - `DJANGO_CSRF_TRUSTED_ORIGINS=https://ljietconference7.pythonanywhere.com`
5. **Error log** — Web tab → Log files → error log (shows the exact Python traceback).
6. Click **Reload**.

## Login Credentials

- **Username:** admin
- **Password:** admin123

## Usage

1. Open http://127.0.0.1:8000/
2. Login with super admin credentials
3. Upload the schedule Excel file
4. Upload your marksheet format template (`EVALUATION FORM *.xlsx`) — optional if default template exists
5. Select track or day from dropdown
6. Click Download to get evaluation marksheets

## Paper ID Format

`TRACK {TrackNo}_{Subsession}_D{Day}_{SerialNo}`

Example: `TRACK 01_01_D1_01`

## Tech Stack

- Django 5.x
- openpyxl
- HTML / CSS / JavaScript
