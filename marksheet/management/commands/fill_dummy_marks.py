import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from marksheet.evaluation_config import SECTION_A_CRITERIA, SECTION_B_CRITERIA
from marksheet.models import Paper, PaperEvaluation, ScheduleUpload
from marksheet.utils.evaluation_service import save_paper_evaluation

User = get_user_model()


class Command(BaseCommand):
    help = 'Fill dummy evaluation marks for all papers in the active schedule (testing/demo).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing evaluations',
        )
        parser.add_argument(
            '--seed',
            type=int,
            default=42,
            help='Random seed for reproducible dummy marks',
        )

    def handle(self, *args, **options):
        schedule = ScheduleUpload.objects.filter(is_active=True).first()
        if not schedule:
            self.stderr.write(self.style.ERROR('No active schedule. Upload schedule first.'))
            return

        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            self.stderr.write(self.style.ERROR('No superuser found. Run create_superadmin first.'))
            return

        papers = Paper.objects.filter(schedule=schedule).order_by('day', 'track_session', 'serial_order')
        if not papers.exists():
            self.stderr.write(self.style.ERROR('No papers in active schedule.'))
            return

        rng = random.Random(options['seed'])
        created = 0
        updated = 0
        skipped = 0
        now = timezone.now()

        for paper in papers:
            existing = PaperEvaluation.objects.filter(paper=paper).first()
            if existing and not options['force']:
                skipped += 1
                continue

            # Varied total between 22 and 48 so Results ranking looks realistic
            target_total = rng.randint(22, 48)
            marks = self._build_marks(rng, target_total)

            if target_total >= 40:
                recommendation = 'accept'
            elif target_total >= 30:
                recommendation = 'minor'
            else:
                recommendation = 'reject'

            data = {
                **marks,
                'recommendation': recommendation,
                'comments': f'Dummy evaluation for {paper.paper_id} (demo data).',
            }

            save_paper_evaluation(
                paper, admin, data, PaperEvaluation.ROLE_ADMIN
            )
            ev = PaperEvaluation.objects.get(paper=paper)
            ev.moderator_entered_at = now
            ev.save(update_fields=['moderator_entered_at'])

            if existing:
                updated += 1
            else:
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done — {created} created, {updated} updated, {skipped} skipped '
            f'({papers.count()} papers total).'
        ))

    def _build_marks(self, rng, target_total):
        fields = [f[0] for f in SECTION_A_CRITERIA + SECTION_B_CRITERIA]
        marks = {f: 0 for f in fields}

        remaining = target_total
        for i, field in enumerate(fields):
            slots_left = len(fields) - i
            if slots_left == 1:
                marks[field] = max(0, min(5, remaining))
            else:
                max_here = min(5, remaining - (slots_left - 1) * 0)
                min_here = max(0, remaining - (slots_left - 1) * 5)
                marks[field] = rng.randint(int(min_here), int(max_here))
                remaining -= marks[field]

        return marks
