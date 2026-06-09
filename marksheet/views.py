from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView, LogoutView
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods

from .models import MarksheetTemplate, Paper, ScheduleUpload
from .utils.excel_generator import generate_marksheet_workbook, resolve_template_path, track_sheet_name
from .utils.excel_parser import parse_schedule_file


def superuser_required(user):
    return user.is_authenticated and user.is_superuser


def _get_active_template_path():
    active_template = MarksheetTemplate.objects.filter(is_active=True).first()
    if active_template and active_template.file:
        return active_template.file.path
    return resolve_template_path()


class AdminLoginView(LoginView):
    template_name = 'marksheet/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('dashboard')

    def form_valid(self, form):
        response = super().form_valid(form)
        if not self.request.user.is_superuser:
            from django.contrib.auth import logout
            logout(self.request)
            form.add_error(None, 'Only super admin can access this system.')
            return self.form_invalid(form)
        return response


@login_required
@user_passes_test(superuser_required)
def dashboard(request):
    active_schedule = ScheduleUpload.objects.filter(is_active=True).first()
    papers = Paper.objects.filter(schedule=active_schedule) if active_schedule else Paper.objects.none()

    tracks = []
    if active_schedule:
        track_data = (
            papers.values('track_session', 'track_name', 'day')
            .distinct()
            .order_by('day', 'track_session')
        )
        for item in track_data:
            count = papers.filter(
                track_session=item['track_session'], day=item['day']
            ).count()
            tracks.append({
                'key': f"{item['day']}|{item['track_session']}",
                'label': f"Day {item['day']} — {item['track_session']} ({item['track_name']}) — {count} papers",
                'track_session': item['track_session'],
                'track_name': item['track_name'],
                'day': item['day'],
                'count': count,
            })

    active_template = MarksheetTemplate.objects.filter(is_active=True).first()
    default_template_exists = resolve_template_path() is not None

    context = {
        'active_schedule': active_schedule,
        'active_template': active_template,
        'default_template_exists': default_template_exists,
        'total_papers': papers.count(),
        'total_tracks': len(tracks),
        'tracks': tracks,
        'days': sorted(set(papers.values_list('day', flat=True))),
        'recent_uploads': ScheduleUpload.objects.all()[:5],
    }
    return render(request, 'marksheet/dashboard.html', context)


@login_required
@user_passes_test(superuser_required)
@require_http_methods(['POST'])
def upload_schedule(request):
    uploaded_file = request.FILES.get('schedule_file')
    if not uploaded_file:
        return JsonResponse({'success': False, 'error': 'Please select an Excel file.'}, status=400)

    if not uploaded_file.name.lower().endswith(('.xlsx', '.xls')):
        return JsonResponse({'success': False, 'error': 'Only .xlsx files are supported.'}, status=400)

    try:
        with transaction.atomic():
            ScheduleUpload.objects.filter(is_active=True).update(is_active=False)

            schedule = ScheduleUpload.objects.create(
                file=uploaded_file,
                is_active=True,
            )

            parsed_papers, tracks = parse_schedule_file(schedule.file.path)

            paper_objects = [
                Paper(schedule=schedule, **paper_data)
                for paper_data in parsed_papers
            ]
            Paper.objects.bulk_create(paper_objects)

            schedule.total_papers = len(paper_objects)
            schedule.total_tracks = len(tracks)
            schedule.save()

        return JsonResponse({
            'success': True,
            'message': f'Successfully imported {len(paper_objects)} papers from {len(tracks)} track sessions.',
            'total_papers': len(paper_objects),
            'total_tracks': len(tracks),
        })
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=500)


@login_required
@user_passes_test(superuser_required)
@require_http_methods(['POST'])
def upload_template(request):
    uploaded_file = request.FILES.get('template_file')
    if not uploaded_file:
        return JsonResponse({'success': False, 'error': 'Please select an Excel template file.'}, status=400)

    if not uploaded_file.name.lower().endswith('.xlsx'):
        return JsonResponse({'success': False, 'error': 'Only .xlsx template files are supported.'}, status=400)

    try:
        template = MarksheetTemplate.objects.create(
            file=uploaded_file,
            name=uploaded_file.name,
            is_active=True,
        )
        return JsonResponse({
            'success': True,
            'message': f'Marksheet template "{template.name}" uploaded successfully.',
            'template_name': template.name,
        })
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=500)


@login_required
@user_passes_test(superuser_required)
def download_track_marksheets(request):
    track_key = request.GET.get('track')
    if not track_key:
        return HttpResponse('Track not selected.', status=400)

    try:
        day, track_session = track_key.split('|', 1)
        day = int(day)
    except ValueError:
        return HttpResponse('Invalid track selection.', status=400)

    active_schedule = ScheduleUpload.objects.filter(is_active=True).first()
    if not active_schedule:
        return HttpResponse('No schedule uploaded.', status=404)

    papers = list(
        Paper.objects.filter(
            schedule=active_schedule,
            day=day,
            track_session=track_session,
        ).order_by('serial_order')
    )

    if not papers:
        return HttpResponse('No papers found for this track.', status=404)

    buffer = generate_marksheet_workbook(
        papers, sheet_name_fn=track_sheet_name, template_path=_get_active_template_path()
    )
    safe_track = track_session.replace(' ', '_')
    filename = f'ICRAET2026_Marksheets_D{day}_{safe_track}.xlsx'

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@user_passes_test(superuser_required)
def download_day_marksheets(request):
    day = request.GET.get('day')
    if not day:
        return HttpResponse('Day not selected.', status=400)

    try:
        day = int(day)
    except ValueError:
        return HttpResponse('Invalid day selection.', status=400)

    active_schedule = ScheduleUpload.objects.filter(is_active=True).first()
    if not active_schedule:
        return HttpResponse('No schedule uploaded.', status=404)

    papers = list(
        Paper.objects.filter(schedule=active_schedule, day=day)
        .order_by('track_session', 'serial_order')
    )

    if not papers:
        return HttpResponse('No papers found for this day.', status=404)

    def day_sheet_name(paper, index):
        return f'D{paper.day}_{paper.track_session}_S{paper.serial_order:02d}'

    buffer = generate_marksheet_workbook(
        papers, sheet_name_fn=day_sheet_name, template_path=_get_active_template_path()
    )
    filename = f'ICRAET2026_Marksheets_Day{day}_AllTracks.xlsx'

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@user_passes_test(superuser_required)
def download_all_marksheets(request):
    active_schedule = ScheduleUpload.objects.filter(is_active=True).first()
    if not active_schedule:
        return HttpResponse('No schedule uploaded.', status=404)

    papers = list(
        Paper.objects.filter(schedule=active_schedule)
        .order_by('day', 'track_session', 'serial_order')
    )

    if not papers:
        return HttpResponse('No papers found.', status=404)

    def all_sheet_name(paper, index):
        return f'D{paper.day}_{paper.track_session}_S{paper.serial_order:02d}'

    buffer = generate_marksheet_workbook(
        papers, sheet_name_fn=all_sheet_name, template_path=_get_active_template_path()
    )
    filename = 'ICRAET2026_Marksheets_All_Days_Tracks.xlsx'

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
