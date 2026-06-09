from django.conf import settings
from django.db import models


class ScheduleUpload(models.Model):
    file = models.FileField(upload_to='schedules/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    total_papers = models.PositiveIntegerField(default=0)
    total_tracks = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'Schedule uploaded {self.uploaded_at:%Y-%m-%d %H:%M}'


class MarksheetTemplate(models.Model):
    file = models.FileField(upload_to='templates/')
    name = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.name or f'Template {self.uploaded_at:%Y-%m-%d %H:%M}'

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.file.name if self.file else 'Evaluation Template'
        if self.is_active:
            MarksheetTemplate.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class Paper(models.Model):
    schedule = models.ForeignKey(
        ScheduleUpload, on_delete=models.CASCADE, related_name='papers'
    )
    day = models.PositiveSmallIntegerField()
    day_label = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=20)
    serial_order = models.PositiveIntegerField(default=0)
    room = models.CharField(max_length=50, blank=True)
    track_session = models.CharField(max_length=50)
    track_name = models.CharField(max_length=200, blank=True)
    paper_title = models.CharField(max_length=500)
    author_name = models.CharField(max_length=300)
    university = models.CharField(max_length=300, blank=True)
    mode = models.CharField(max_length=50, blank=True)
    session_chair = models.CharField(max_length=200, blank=True)
    time_slot = models.CharField(max_length=50, blank=True)
    paper_id = models.CharField(max_length=50)
    track_session_display = models.CharField(max_length=50)

    class Meta:
        ordering = ['day', 'track_session', 'serial_order']

    def __str__(self):
        return f'{self.paper_id} - {self.paper_title[:50]}'


class TrackDuty(models.Model):
    schedule = models.ForeignKey(
        ScheduleUpload, on_delete=models.CASCADE, related_name='track_duties'
    )
    day = models.PositiveSmallIntegerField()
    day_label = models.CharField(max_length=100, blank=True)
    room = models.CharField(max_length=50)
    track_session = models.CharField(max_length=50)
    track_name = models.CharField(max_length=200, blank=True)
    verifier = models.CharField(max_length=200, blank=True)
    session_chair = models.CharField(max_length=200, blank=True)
    track_coordinator = models.CharField(max_length=200, blank=True)
    moderator_1 = models.CharField(max_length=200, blank=True)
    moderator_2 = models.CharField(max_length=200, blank=True)
    moderator_3 = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['day', 'track_session', 'room']

    def __str__(self):
        return f'Day {self.day} — {self.track_session} — {self.room}'


class TrackSessionLock(models.Model):
    schedule = models.ForeignKey(
        ScheduleUpload, on_delete=models.CASCADE, related_name='track_locks'
    )
    day = models.PositiveSmallIntegerField()
    track_session = models.CharField(max_length=50)
    is_locked = models.BooleanField(default=False)
    locked_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='track_locks',
    )

    class Meta:
        unique_together = [('schedule', 'day', 'track_session')]

    def __str__(self):
        status = 'Locked' if self.is_locked else 'Open'
        return f'Day {self.day} {self.track_session} — {status}'


class FacultyProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='faculty_profile'
    )
    display_name = models.CharField(max_length=200)
    normalized_name = models.CharField(max_length=200, db_index=True)
    plain_password = models.CharField(max_length=10, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    schedule = models.ForeignKey(
        ScheduleUpload, on_delete=models.CASCADE, related_name='faculty_profiles', null=True, blank=True
    )

    class Meta:
        ordering = ['display_name']

    def __str__(self):
        return self.display_name


class VerifierProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='verifier_profile'
    )
    display_name = models.CharField(max_length=200)
    normalized_name = models.CharField(max_length=200, db_index=True)
    plain_password = models.CharField(max_length=10, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    schedule = models.ForeignKey(
        ScheduleUpload, on_delete=models.CASCADE, related_name='verifier_profiles', null=True, blank=True
    )

    class Meta:
        ordering = ['display_name']

    def __str__(self):
        return self.display_name


class PaperEvaluation(models.Model):
    ROLE_MODERATOR = 'moderator2'
    ROLE_VERIFIER = 'verifier'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = [
        (ROLE_MODERATOR, 'Moderator-2'),
        (ROLE_VERIFIER, 'Verifier'),
        (ROLE_ADMIN, 'Admin'),
    ]

    RECOMMENDATION_ACCEPT = 'accept'
    RECOMMENDATION_MINOR = 'minor'
    RECOMMENDATION_REJECT = 'reject'
    RECOMMENDATION_CHOICES = [
        (RECOMMENDATION_ACCEPT, 'ACCEPT'),
        (RECOMMENDATION_MINOR, 'MINOR REVISION'),
        (RECOMMENDATION_REJECT, 'REJECT'),
    ]

    paper = models.OneToOneField(Paper, on_delete=models.CASCADE, related_name='evaluation')
    evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='paper_evaluations',
    )
    last_role = models.CharField(max_length=12, choices=ROLE_CHOICES, blank=True)
    moderator_entered_at = models.DateTimeField(null=True, blank=True)
    verifier_modified_at = models.DateTimeField(null=True, blank=True)
    pres_clarity = models.PositiveSmallIntegerField(null=True, blank=True)
    originality = models.PositiveSmallIntegerField(null=True, blank=True)
    technical_knowledge = models.PositiveSmallIntegerField(null=True, blank=True)
    time_management = models.PositiveSmallIntegerField(null=True, blank=True)
    qa_handling = models.PositiveSmallIntegerField(null=True, blank=True)
    novelty = models.PositiveSmallIntegerField(null=True, blank=True)
    methodology = models.PositiveSmallIntegerField(null=True, blank=True)
    result_validation = models.PositiveSmallIntegerField(null=True, blank=True)
    impact = models.PositiveSmallIntegerField(null=True, blank=True)
    paper_quality = models.PositiveSmallIntegerField(null=True, blank=True)
    recommendation = models.CharField(max_length=10, choices=RECOMMENDATION_CHOICES, blank=True)
    comments = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.paper.paper_id} evaluation'

    @property
    def section_a_total(self):
        fields = [
            self.pres_clarity, self.originality, self.technical_knowledge,
            self.time_management, self.qa_handling,
        ]
        if any(v is None for v in fields):
            return None
        return sum(fields)

    @property
    def section_b_total(self):
        fields = [
            self.novelty, self.methodology, self.result_validation,
            self.impact, self.paper_quality,
        ]
        if any(v is None for v in fields):
            return None
        return sum(fields)

    @property
    def final_score(self):
        a = self.section_a_total
        b = self.section_b_total
        if a is None or b is None:
            return None
        return a + b

    @property
    def is_complete(self):
        return self.final_score is not None and bool(self.recommendation)
