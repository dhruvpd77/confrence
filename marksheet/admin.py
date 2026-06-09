from django.contrib import admin
from .models import MarksheetTemplate, Paper, ScheduleUpload


@admin.register(ScheduleUpload)
class ScheduleUploadAdmin(admin.ModelAdmin):
    list_display = ('id', 'uploaded_at', 'total_papers', 'total_tracks', 'is_active')
    list_filter = ('is_active',)


@admin.register(MarksheetTemplate)
class MarksheetTemplateAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'uploaded_at', 'is_active')
    list_filter = ('is_active',)


@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    list_display = (
        'paper_id', 'paper_title', 'author_name', 'track_session',
        'day', 'serial_number',
    )
    list_filter = ('day', 'track_session')
    search_fields = ('paper_id', 'paper_title', 'author_name')
