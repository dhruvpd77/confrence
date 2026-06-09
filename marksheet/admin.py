from django.contrib import admin

from .models import (
    FacultyProfile,
    MarksheetTemplate,
    Paper,
    PaperEvaluation,
    ScheduleUpload,
    TrackDuty,
    TrackSessionLock,
    VerifierProfile,
)


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


@admin.register(TrackDuty)
class TrackDutyAdmin(admin.ModelAdmin):
    list_display = ('day', 'track_session', 'room', 'track_coordinator', 'moderator_2')
    list_filter = ('day', 'track_session')


@admin.register(FacultyProfile)
class FacultyProfileAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'user', 'plain_password', 'phone')
    search_fields = ('display_name', 'user__username')


@admin.register(PaperEvaluation)
class PaperEvaluationAdmin(admin.ModelAdmin):
    list_display = ('paper', 'evaluator', 'last_role', 'final_score', 'moderator_entered_at', 'updated_at')
    list_filter = ('recommendation', 'last_role')


@admin.register(VerifierProfile)
class VerifierProfileAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'user', 'plain_password')
    search_fields = ('display_name', 'user__username')


@admin.register(TrackSessionLock)
class TrackSessionLockAdmin(admin.ModelAdmin):
    list_display = ('day', 'track_session', 'is_locked', 'locked_at', 'locked_by')
    list_filter = ('is_locked', 'day')
