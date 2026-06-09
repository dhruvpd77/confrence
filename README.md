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

## Setup

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py create_superadmin
python manage.py runserver
```

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
