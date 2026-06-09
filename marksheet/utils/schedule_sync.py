"""Merge schedule Excel re-uploads without losing evaluations when papers still match."""

from marksheet.models import Paper, PaperEvaluation

PAPER_SYNC_FIELDS = (
    'day',
    'day_label',
    'serial_number',
    'serial_order',
    'room',
    'track_session',
    'track_name',
    'paper_title',
    'author_name',
    'university',
    'mode',
    'session_chair',
    'time_slot',
    'track_session_display',
)


def sync_papers(schedule, parsed_papers):
    """
    Upsert papers by paper_id on the same schedule.
    Existing evaluations stay linked when paper_id is unchanged.
    Papers removed from the Excel are deleted (evaluations cascade).
    """
    old_by_id = {
        p.paper_id: p
        for p in Paper.objects.filter(schedule=schedule)
    }
    new_ids = set()
    created = 0
    updated = 0
    unchanged = 0
    evaluations_preserved = 0

    for data in parsed_papers:
        paper_id = data['paper_id']
        new_ids.add(paper_id)

        if paper_id in old_by_id:
            paper = old_by_id[paper_id]
            if PaperEvaluation.objects.filter(paper_id=paper.pk).exists():
                evaluations_preserved += 1

            changed = False
            for field in PAPER_SYNC_FIELDS:
                new_value = data.get(field, '')
                if getattr(paper, field) != new_value:
                    setattr(paper, field, new_value)
                    changed = True
            if changed:
                paper.save(update_fields=list(PAPER_SYNC_FIELDS))
                updated += 1
            else:
                unchanged += 1
        else:
            Paper.objects.create(schedule=schedule, **data)
            created += 1

    removed_qs = Paper.objects.filter(schedule=schedule).exclude(paper_id__in=new_ids)
    removed = removed_qs.count()
    removed_qs.delete()

    return {
        'created': created,
        'updated': updated,
        'unchanged': unchanged,
        'removed': removed,
        'evaluations_preserved': evaluations_preserved,
        'total': len(new_ids),
    }
