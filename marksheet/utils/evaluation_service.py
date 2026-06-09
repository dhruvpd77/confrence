from django.utils import timezone

from marksheet.models import Paper, PaperEvaluation


def get_paper_evaluation(paper):
    return PaperEvaluation.objects.filter(paper=paper).first()


def get_evaluations_for_papers(papers):
    paper_ids = [p.id for p in papers]
    return {ev.paper_id: ev for ev in PaperEvaluation.objects.filter(paper_id__in=paper_ids)}


def save_paper_evaluation(paper, user, data, role):
    evaluation, created = PaperEvaluation.objects.get_or_create(
        paper=paper,
        defaults={'evaluator': user, 'last_role': role},
    )
    for field, value in data.items():
        setattr(evaluation, field, value)
    evaluation.evaluator = user
    evaluation.last_role = role
    now = timezone.now()
    if role == PaperEvaluation.ROLE_MODERATOR:
        if not evaluation.moderator_entered_at:
            evaluation.moderator_entered_at = now
    elif role == PaperEvaluation.ROLE_VERIFIER:
        evaluation.verifier_modified_at = now
    elif role == PaperEvaluation.ROLE_ADMIN:
        if not evaluation.moderator_entered_at:
            evaluation.moderator_entered_at = now
    evaluation.save()
    return evaluation
