"""Track-session background colors for Excel exports."""

import re

from openpyxl.styles import PatternFill

# Distinct pastel colors per track session
TRACK_PALETTE = [
    'D6EAF8',  # blue
    'D5F5E3',  # green
    'FDEBD0',  # orange
    'E8DAEF',  # purple
    'FCF3CF',  # gold
    'D1F2EB',  # teal
    'F9E79F',  # yellow
    'F5B7B1',  # coral
    'D7BDE2',  # lavender
    'A9DFBF',  # mint
    'AED6F1',  # sky
    'FAD7A0',  # peach
    'FADBD8',  # rose (poster default)
    'E8F8F5',  # aqua
    'EBF5FB',  # light blue
    'F5EEF8',  # lilac
    'FEF9E7',  # cream
    'EAEDED',  # silver
]

TRACK_POSTER_COLOR = 'FADBD8'
TRACK_DEFAULT_COLOR = 'F2F3F4'

_fill_cache = {}


def get_track_color_hex(track_session, track_name=''):
    text = f'{track_session} {track_name}'.upper()
    if 'POSTER' in text:
        return TRACK_POSTER_COLOR

    match = re.search(r'TRACK\s*(\d+)_(\d+)', text, re.I)
    if match:
        track_num, sub = int(match.group(1)), int(match.group(2))
        idx = ((track_num - 1) * 8 + (sub - 1)) % len(TRACK_PALETTE)
        return TRACK_PALETTE[idx]

    match = re.search(r'TRACK\s*(\d+)', text, re.I)
    if match:
        idx = (int(match.group(1)) - 1) % len(TRACK_PALETTE)
        return TRACK_PALETTE[idx]

    session = (track_session or '').strip().lower()
    if session and session not in ('', 'poster'):
        idx = sum(ord(c) for c in session) % len(TRACK_PALETTE)
        return TRACK_PALETTE[idx]

    return TRACK_DEFAULT_COLOR


def get_track_row_fill(track_session, track_name=''):
    color = get_track_color_hex(track_session, track_name)
    if color not in _fill_cache:
        _fill_cache[color] = PatternFill(
            start_color=color, end_color=color, fill_type='solid'
        )
    return _fill_cache[color]
