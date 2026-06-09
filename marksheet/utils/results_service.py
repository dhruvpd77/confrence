"""Top scorers by evaluation marks for admin Results page."""


def is_poster_paper(paper):
    if (paper.paper_id or '').upper().startswith('POSTER_'):
        return True
    session = (paper.track_session or '').upper()
    name = (paper.track_name or '').upper()
    return 'POSTER' in session or 'POSTER' in name


def get_top_scored_papers(papers_qs, paper_type='all', limit=5):
    """
    Return top `limit` papers with completed scores, highest marks first.
    paper_type: 'all' | 'poster' | 'paper'
    """
    if paper_type not in ('all', 'poster', 'paper'):
        paper_type = 'all'

    rows = []
    for paper in papers_qs.select_related('evaluation'):
        evaluation = getattr(paper, 'evaluation', None)
        if not evaluation or evaluation.final_score is None:
            continue

        poster = is_poster_paper(paper)
        if paper_type == 'poster' and not poster:
            continue
        if paper_type == 'paper' and poster:
            continue

        rows.append({
            'paper': paper,
            'score': evaluation.final_score,
            'author': paper.author_name,
            'title': paper.paper_title,
            'paper_id': paper.paper_id,
            'day': paper.day,
            'track_session': paper.track_session,
            'track_name': paper.track_name,
            'type_label': 'Poster' if poster else 'Paper',
        })

    rows.sort(key=lambda r: (-r['score'], r['paper'].serial_order, r['paper_id']))
    top = rows[:limit]
    for index, row in enumerate(top, start=1):
        row['rank'] = index
    return top
