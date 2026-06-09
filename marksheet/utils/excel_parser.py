import re
from openpyxl import load_workbook


def _extract_day_info(sheet_name):
    name_upper = sheet_name.upper()
    if 'DAY 1' in name_upper or '12 JUNE' in name_upper:
        return 1, sheet_name
    if 'DAY 2' in name_upper or '13 JUNE' in name_upper:
        return 2, sheet_name
    return None, sheet_name


def _parse_track_session(track_session):
    if not track_session:
        return None, None, None
    text = str(track_session).strip()

    match = re.match(r'[Tt][Rr][Aa][Cc][Kk]\s*(\d+)_(\d+)', text)
    if match:
        track_num = int(match.group(1))
        subsession = int(match.group(2))
        display = f'TRACK {track_num:02d}_{subsession:02d}'
        return track_num, subsession, display

    poster_match = re.match(r'[Pp][Oo][Ss][Tt][Ee][Rr]_?(\d+)', text)
    if poster_match:
        poster_num = int(poster_match.group(1))
        display = f'POSTER_{poster_num:02d}'
        return poster_num, 0, display

    if 'POSTER' in text.upper():
        return 0, 0, text.upper().replace(' ', '_')

    return None, None, None


def _parse_serial(sr_value):
    if sr_value is None:
        return None, 0
    sr_str = str(sr_value).strip()
    if not sr_str or sr_str.upper() in ('SR', 'TIME'):
        return None, 0
    match = re.match(r'^(\d+)', sr_str)
    if not match:
        return None, 0
    return sr_str, int(match.group(1))


def generate_paper_id(track_session, day_num, serial_number):
    text = str(track_session or '').strip()
    track_num, subsession, display = _parse_track_session(track_session)
    if track_num is None:
        return '', ''

    _, serial_order = _parse_serial(serial_number)

    if re.match(r'[Pp][Oo][Ss][Tt][Ee][Rr]', text):
        poster_match = re.match(r'[Pp][Oo][Ss][Tt][Ee][Rr]_?(\d+)', text)
        poster_num = int(poster_match.group(1)) if poster_match else track_num
        paper_id = f'POSTER_{poster_num:02d}_D{day_num}_{serial_order:02d}'
        return paper_id, f'POSTER_{poster_num:02d}'

    paper_id = f'TRACK {track_num:02d}_{subsession:02d}_D{day_num}_{serial_order:02d}'
    return paper_id, display


def _is_track_header_row(sr_value, track_session):
    sr_str = str(sr_value or '').strip()
    if '|' in sr_str:
        return True
    if track_session and re.match(r'[Tt]rack\s*\d+_\d+', str(track_session)):
        paper_title_missing = True
        return sr_str and not sr_str.replace('.', '').isdigit() and '|' in sr_str
    return False


def parse_schedule_file(file_path):
    workbook = load_workbook(file_path, data_only=True)
    papers = []
    tracks = set()

    for sheet_name in workbook.sheetnames:
        day_num, day_label = _extract_day_info(sheet_name)
        if day_num is None:
            continue

        worksheet = workbook[sheet_name]
        current_track_session = ''
        current_track_name = ''
        current_room = ''
        current_session_chair = ''

        for row in range(3, worksheet.max_row + 1):
            sr = worksheet.cell(row, 1).value
            room = worksheet.cell(row, 2).value
            track_session = worksheet.cell(row, 3).value
            paper_title = worksheet.cell(row, 4).value
            author_name = worksheet.cell(row, 5).value
            university = worksheet.cell(row, 6).value or ''
            mode = worksheet.cell(row, 7).value or ''
            session_chair = worksheet.cell(row, 8).value or ''
            time_slot = worksheet.cell(row, 13).value or ''

            sr_str = str(sr or '').strip()

            if sr_str and '|' in sr_str:
                parts = sr_str.split('|')
                current_room = parts[0].strip()
                if len(parts) > 1:
                    header_track = parts[1].strip()
                    if re.match(r'[Tt]rack\s*\d+_\d+', header_track):
                        current_track_session = header_track
                elif track_session:
                    current_track_session = str(track_session).strip()
                if track_session and 'Track' in str(track_session):
                    current_track_name = str(track_session).strip()
                elif track_session and 'POSTER' in str(track_session).upper():
                    current_track_name = str(track_session).strip()
                    if not current_track_session or 'POSTER' not in current_track_session.upper():
                        current_track_session = 'POSTER PRESENTATION'
                if session_chair:
                    current_session_chair = str(session_chair).strip()
                tracks.add((current_track_session, current_track_name, day_num))
                continue

            serial_number, serial_order = _parse_serial(sr)
            if serial_number is None or not paper_title or not author_name:
                continue

            if track_session and re.match(r'[Tt]rack\s*\d+_\d+', str(track_session)):
                current_track_session = str(track_session).strip()
            elif track_session and re.match(r'[Pp][Oo][Ss][Tt][Ee][Rr]', str(track_session)):
                current_track_session = str(track_session).strip()
                if not current_track_name:
                    current_track_name = 'Poster Presentation'

            if room:
                current_room = str(room).strip()
            if session_chair:
                current_session_chair = str(session_chair).strip()

            if not current_track_session:
                continue

            paper_id, track_display = generate_paper_id(
                current_track_session, day_num, serial_number
            )
            if not paper_id:
                continue

            tracks.add((current_track_session, current_track_name, day_num))

            papers.append({
                'day': day_num,
                'day_label': day_label,
                'serial_number': serial_number,
                'serial_order': serial_order,
                'room': current_room,
                'track_session': current_track_session,
                'track_name': current_track_name,
                'paper_title': str(paper_title).strip(),
                'author_name': str(author_name).strip(),
                'university': str(university).strip(),
                'mode': str(mode).strip(),
                'session_chair': current_session_chair,
                'time_slot': str(time_slot).strip() if time_slot else '',
                'paper_id': paper_id,
                'track_session_display': track_display,
            })

    return papers, tracks
