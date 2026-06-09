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
