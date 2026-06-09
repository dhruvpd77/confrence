from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_http_methods

from .decorators import (
    admin_required,
    faculty_login_required,
    faculty_required,
    superuser_required,
    verifier_login_required,
    verifier_required,
)
from .evaluation_config import RECOMMENDATION_OPTIONS, SECTION_A_CRITERIA, SECTION_B_CRITERIA
from .models import FacultyProfile, MarksheetTemplate, Paper, PaperEvaluation, ScheduleUpload, TrackDuty, TrackSessionLock
from .utils.evaluation_report import (
    build_evaluation_report_rows,
    generate_evaluation_report_workbook,
    get_evaluations_map,
)
from .utils.results_service import get_top_scored_papers
from .utils.schedule_sync import sync_papers
from .utils.evaluation_service import get_evaluations_for_papers, get_paper_evaluation, save_paper_evaluation
from .utils.track_lock import get_locks_map, is_track_locked, lock_track
from .utils.credential_email import send_credential_emails
from .utils.credentials_service import (
    build_moderator_credential_rows,
    build_verifier_credential_rows,
    credential_stats,
    group_moderator_email_recipients,
    group_verifier_email_recipients,
)
from .utils.verifier_credentials import (
    generate_verifier_credentials_workbook,
    get_track_verifier_contact,
    get_verifier_duties,
    get_verifier_profiles,
    get_verifier_track_keys,
    sync_verifier_users,
)
from .utils.verifier_parser import apply_verifier_assignments, parse_verifier_assignments
from .utils.excel_generator import generate_marksheet_workbook, resolve_template_path, track_sheet_name
from .utils.excel_parser import parse_schedule_file
from .utils.faculty_credentials import (
    generate_credentials_workbook,
    get_faculty_duties,
    get_faculty_track_keys,
    get_moderator2_profiles,
    sync_faculty_users,
    sync_track_duties,
)
from .utils.track_duty_generator import generate_track_duty_workbook, parse_track_duty


def _get_active_template_path():
    active_template = MarksheetTemplate.objects.filter(is_active=True).first()
    if active_template and active_template.file:
        try:
            if active_template.file.storage.exists(active_template.file.name):
                return active_template.file.path
        except (ValueError, OSError):
            pass
    return resolve_template_path()


def _get_template_status():
    active_template = MarksheetTemplate.objects.filter(is_active=True).first()
    if active_template and active_template.file:
        try:
            if active_template.file.storage.exists(active_template.file.name):
                return {
                    'name': active_template.name,
                    'source': 'uploaded',
                    'ready': True,
                }
        except (ValueError, OSError):
            pass
    bundled = resolve_template_path()
    if bundled:
        return {
            'name': bundled.name,
            'source': 'bundled',
            'ready': True,
        }
    return {'name': '', 'source': 'none', 'ready': False}


def _get_active_schedule():
    return ScheduleUpload.objects.filter(is_active=True).first()


def _format_track_option_label(day, track_session, track_name, count, locked_label=''):
    if track_name and '|' in track_name:
        label = f'Day {day} — {track_name} — {count} papers'
    elif track_name and track_name != track_session:
        label = f'Day {day} — {track_session} ({track_name}) — {count} papers'
    else:
        label = f'Day {day} — {track_session} — {count} papers'
    return f'{label}{locked_label}'


def _build_track_options(papers):
    tracks = []
    if not papers.exists():
        return tracks
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
            'label': _format_track_option_label(
                item['day'], item['track_session'], item['track_name'], count
            ),
            'track_session': item['track_session'],
            'track_name': item['track_name'],
            'day': item['day'],
            'count': count,
        })
    return tracks


def _parse_evaluation_form(request):
    data = {}
    for field, _, _ in SECTION_A_CRITERIA + SECTION_B_CRITERIA:
        raw = request.POST.get(field)
        if raw:
            try:
                value = int(raw)
                if 0 <= value <= 5:
                    data[field] = value
            except ValueError:
                pass
    recommendation = request.POST.get('recommendation', '')
    if recommendation in dict(RECOMMENDATION_OPTIONS):
        data['recommendation'] = recommendation
    data['comments'] = request.POST.get('comments', '').strip()
    return data


class AdminLoginView(LoginView):
    template_name = 'marksheet/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if user.is_superuser:
            return reverse_lazy('dashboard')
        if verifier_required(user):
            return reverse_lazy('verifier_dashboard')
        if faculty_required(user):
            return reverse_lazy('faculty_dashboard')
        return reverse_lazy('login')

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user
        if not user.is_superuser and not faculty_required(user) and not verifier_required(user):
            from django.contrib.auth import logout
            logout(self.request)
            form.add_error(None, 'Invalid credentials.')
            return self.form_invalid(form)
        return response


@admin_required
def dashboard(request):
    active_schedule = _get_active_schedule()
    papers = Paper.objects.filter(schedule=active_schedule) if active_schedule else Paper.objects.none()
    tracks = _build_track_options(papers)
    template_status = _get_template_status()
    faculty_count = get_moderator2_profiles(active_schedule).count() if active_schedule else 0
    verifier_count = get_verifier_profiles(active_schedule).count() if active_schedule else 0
    verifier_assigned = TrackDuty.objects.filter(
        schedule=active_schedule
    ).exclude(verifier='').count() if active_schedule else 0

    context = {
        'active_schedule': active_schedule,
        'template_status': template_status,
        'active_template': template_status if template_status['ready'] else None,
        'total_papers': papers.count(),
        'total_tracks': len(tracks),
        'tracks': tracks,
        'days': sorted(set(papers.values_list('day', flat=True))),
        'recent_uploads': ScheduleUpload.objects.all()[:5],
        'faculty_count': faculty_count,
        'verifier_count': verifier_count,
        'verifier_assigned': verifier_assigned,
        'sidebar_active': 'dashboard',
        'is_admin': True,
    }
    return render(request, 'marksheet/dashboard.html', context)


@faculty_login_required
def faculty_dashboard(request):
    profile = request.user.faculty_profile
    active_schedule = _get_active_schedule() or profile.schedule
    selected_day = request.GET.get('day')
    try:
        selected_day = int(selected_day) if selected_day else None
    except ValueError:
        selected_day = None

    duties = get_faculty_duties(profile, schedule=active_schedule, day=selected_day)
    days = sorted(set(
        TrackDuty.objects.filter(schedule=active_schedule).values_list('day', flat=True)
    )) if active_schedule else []

    context = {
        'profile': profile,
        'duties': duties,
        'days': days,
        'selected_day': selected_day,
        'active_schedule': active_schedule,
        'sidebar_active': 'duties',
        'is_admin': False,
    }
    return render(request, 'marksheet/faculty_dashboard.html', context)


@faculty_login_required
def faculty_evaluations(request):
    profile = request.user.faculty_profile
    active_schedule = _get_active_schedule() or profile.schedule
    track_keys = get_faculty_track_keys(profile, schedule=active_schedule)
    track_key = request.GET.get('track')

    track_options = []
    papers = []
    selected_track = None
    track_locked = False
    verifier_info = None

    if active_schedule and track_keys:
        all_papers = Paper.objects.filter(schedule=active_schedule)
        for day, track_session in sorted(track_keys):
            key = f'{day}|{track_session}'
            count = all_papers.filter(day=day, track_session=track_session).count()
            sample = all_papers.filter(day=day, track_session=track_session).first()
            track_name = sample.track_name if sample else ''
            track_options.append({
                'key': key,
                'label': _format_track_option_label(day, track_session, track_name, count),
            })

        if track_key and '|' in track_key:
            day_str, track_session = track_key.split('|', 1)
            try:
                day = int(day_str)
            except ValueError:
                day = None
            if day and (day, track_session) in track_keys:
                papers = list(
                    all_papers.filter(day=day, track_session=track_session)
                    .order_by('serial_order')
                )
                selected_track = track_key
                evaluations = get_evaluations_for_papers(papers)
                track_locked = is_track_locked(active_schedule, day, track_session)
                verifier_info = get_track_verifier_contact(active_schedule, day, track_session)
                for paper in papers:
                    paper.user_evaluation = evaluations.get(paper.id)
                    paper.eval_status = (
                        'Completed' if paper.user_evaluation and paper.user_evaluation.is_complete
                        else 'Pending'
                    )
                    paper.track_locked = track_locked

    context = {
        'profile': profile,
        'track_options': track_options,
        'selected_track': selected_track,
        'papers': papers,
        'verifier_info': verifier_info,
        'track_locked': track_locked,
        'sidebar_active': 'evaluations',
        'is_admin': False,
    }
    return render(request, 'marksheet/faculty_evaluations.html', context)


@login_required
def evaluation_form(request, paper_id):
    paper = get_object_or_404(Paper, pk=paper_id)
    is_admin = superuser_required(request.user)
    is_verifier = verifier_required(request.user)
    is_faculty = faculty_required(request.user)
    role = PaperEvaluation.ROLE_ADMIN
    back_url_name = 'admin_evaluations'

    if is_verifier:
        role = PaperEvaluation.ROLE_VERIFIER
        back_url_name = 'verifier_evaluations'
        profile = request.user.verifier_profile
        track_keys = get_verifier_track_keys(profile, schedule=paper.schedule, day=paper.day)
        if (paper.day, paper.track_session) not in track_keys:
            return HttpResponse('You are not assigned to verify this track session.', status=403)
    elif is_faculty:
        role = PaperEvaluation.ROLE_MODERATOR
        back_url_name = 'faculty_evaluations'
        profile = request.user.faculty_profile
        track_keys = get_faculty_track_keys(profile, schedule=paper.schedule, day=paper.day)
        if (paper.day, paper.track_session) not in track_keys:
            return HttpResponse('You are not assigned to this track session.', status=403)
        if is_track_locked(paper.schedule, paper.day, paper.track_session):
            return HttpResponse('This track is locked by the verifier. Editing is not allowed.', status=403)
    elif not is_admin:
        return redirect('login')

    evaluation = get_paper_evaluation(paper)
    track_lock = TrackSessionLock.objects.filter(
        schedule=paper.schedule,
        day=paper.day,
        track_session=paper.track_session,
        is_locked=True,
    ).first()

    if request.method == 'POST':
        if is_faculty and is_track_locked(paper.schedule, paper.day, paper.track_session):
            return HttpResponse('This track is locked. You cannot edit marks.', status=403)
        data = _parse_evaluation_form(request)
        evaluation = save_paper_evaluation(paper, request.user, data, role)
        return redirect(f"{reverse(back_url_name)}?track={paper.day}|{paper.track_session}")

    eval_values = {}
    if evaluation:
        for field, _, _ in SECTION_A_CRITERIA + SECTION_B_CRITERIA:
            val = getattr(evaluation, field, None)
            eval_values[field] = val if val is not None else ''

    context = {
        'paper': paper,
        'evaluation': evaluation,
        'eval_values': eval_values,
        'section_a': SECTION_A_CRITERIA,
        'section_b': SECTION_B_CRITERIA,
        'recommendations': RECOMMENDATION_OPTIONS,
        'sidebar_active': 'evaluations',
        'is_admin': is_admin,
        'is_verifier': is_verifier,
        'is_faculty': is_faculty,
        'track_locked': bool(track_lock),
        'track_lock': track_lock,
        'read_only': is_faculty and bool(track_lock),
        'back_url_name': back_url_name,
    }
    return render(request, 'marksheet/evaluation_form.html', context)


@admin_required
def admin_evaluations(request):
    active_schedule = _get_active_schedule()
    papers_qs = Paper.objects.filter(schedule=active_schedule) if active_schedule else Paper.objects.none()
    track_key = request.GET.get('track')
    track_options = _build_track_options(papers_qs)
    papers = []

    if track_key and '|' in track_key:
        day_str, track_session = track_key.split('|', 1)
        try:
            day = int(day_str)
        except ValueError:
            day = None
        if day:
            papers = list(
                papers_qs.filter(day=day, track_session=track_session)
                .order_by('serial_order')
            )
            evaluations = get_evaluations_for_papers(papers)
            for paper in papers:
                paper.user_evaluation = evaluations.get(paper.id)
                paper.eval_status = (
                    'Completed' if paper.user_evaluation and paper.user_evaluation.is_complete
                    else 'Pending'
                )

    context = {
        'track_options': track_options,
        'selected_track': track_key,
        'papers': papers,
        'sidebar_active': 'evaluations',
        'is_admin': True,
    }
    return render(request, 'marksheet/admin_evaluations.html', context)


@admin_required
def evaluation_report(request):
    active_schedule = _get_active_schedule()
    papers_qs = Paper.objects.filter(schedule=active_schedule) if active_schedule else Paper.objects.none()

    day = request.GET.get('day')
    track_key = request.GET.get('track')
    faculty_id = request.GET.get('faculty')

    try:
        day = int(day) if day else None
    except ValueError:
        day = None
    try:
        faculty_id = int(faculty_id) if faculty_id else None
    except ValueError:
        faculty_id = None

    filtered = papers_qs
    if day:
        filtered = filtered.filter(day=day)
    if track_key and '|' in track_key:
        day_str, track_session = track_key.split('|', 1)
        try:
            filtered = filtered.filter(day=int(day_str), track_session=track_session)
        except ValueError:
            pass

    if faculty_id:
        profile = FacultyProfile.objects.filter(user_id=faculty_id).first()
        if profile:
            track_keys = get_faculty_track_keys(profile, schedule=active_schedule, day=day)
            if track_keys:
                track_filter = Q()
                for duty_day, track_session in track_keys:
                    track_filter |= Q(day=duty_day, track_session=track_session)
                filtered = filtered.filter(track_filter)
        evaluations_map = get_evaluations_for_papers(list(filtered))
    else:
        evaluations_map = get_evaluations_for_papers(list(filtered))

    locks_map = get_locks_map(active_schedule, day=day) if active_schedule else {}
    rows = build_evaluation_report_rows(
        list(filtered.order_by('day', 'track_session', 'serial_order')),
        evaluations_map,
        locks_map=locks_map,
    )

    faculty_list = list(get_moderator2_profiles(active_schedule)) if active_schedule else []
    track_options = _build_track_options(papers_qs)
    days = sorted(set(papers_qs.values_list('day', flat=True)))

    context = {
        'rows': rows,
        'days': days,
        'track_options': track_options,
        'faculty_list': faculty_list,
        'selected_day': day,
        'selected_track': track_key,
        'selected_faculty': faculty_id,
        'sidebar_active': 'reports',
        'is_admin': True,
        'pending_count': sum(1 for r in rows if r['status'] == 'Pending'),
        'completed_count': sum(1 for r in rows if r['status'] == 'Completed'),
    }
    return render(request, 'marksheet/evaluation_report.html', context)


@admin_required
def results_ranking(request):
    active_schedule = _get_active_schedule()
    papers_qs = Paper.objects.filter(schedule=active_schedule) if active_schedule else Paper.objects.none()

    day = request.GET.get('day')
    track_key = request.GET.get('track')
    paper_type = request.GET.get('type', 'all')

    try:
        day = int(day) if day else None
    except ValueError:
        day = None

    if paper_type not in ('all', 'poster', 'paper'):
        paper_type = 'all'

    filtered = papers_qs
    if day:
        filtered = filtered.filter(day=day)
    if track_key and '|' in track_key:
        day_str, track_session = track_key.split('|', 1)
        try:
            filtered = filtered.filter(day=int(day_str), track_session=track_session)
        except ValueError:
            pass

    track_options_qs = papers_qs.filter(day=day) if day else papers_qs
    days = sorted(set(papers_qs.values_list('day', flat=True)))
    top_results = get_top_scored_papers(filtered, paper_type=paper_type, limit=5)

    parts = []
    if day:
        parts.append(f'Day {day}')
    else:
        parts.append('All Days')
    if track_key and '|' in track_key:
        sample = filtered.first()
        parts.append(sample.track_name if sample and sample.track_name else track_key.split('|', 1)[1])
    else:
        parts.append('All Tracks')
    if paper_type == 'poster':
        parts.append('Posters')
    elif paper_type == 'paper':
        parts.append('Papers')
    else:
        parts.append('Papers + Posters')

    context = {
        'top_results': top_results,
        'days': days,
        'track_options': _build_track_options(track_options_qs),
        'selected_day': day,
        'selected_track': track_key,
        'selected_type': paper_type,
        'filter_summary': ' · '.join(parts),
        'sidebar_active': 'results',
        'is_admin': True,
    }
    return render(request, 'marksheet/results.html', context)


@admin_required
def download_evaluation_report(request):
    active_schedule = _get_active_schedule()
    if not active_schedule:
        return HttpResponse('No schedule uploaded.', status=404)

    papers_qs = Paper.objects.filter(schedule=active_schedule)
    day = request.GET.get('day')
    track_key = request.GET.get('track')
    faculty_id = request.GET.get('faculty')

    try:
        day = int(day) if day else None
    except ValueError:
        day = None
    try:
        faculty_id = int(faculty_id) if faculty_id else None
    except ValueError:
        faculty_id = None

    if day:
        papers_qs = papers_qs.filter(day=day)
    if track_key and '|' in track_key:
        day_str, track_session = track_key.split('|', 1)
        try:
            papers_qs = papers_qs.filter(day=int(day_str), track_session=track_session)
        except ValueError:
            pass

    if faculty_id:
        profile = FacultyProfile.objects.filter(user_id=faculty_id).first()
        if profile:
            track_keys = get_faculty_track_keys(profile, schedule=active_schedule, day=day)
            if track_keys:
                track_filter = Q()
                for duty_day, track_session in track_keys:
                    track_filter |= Q(day=duty_day, track_session=track_session)
                papers_qs = papers_qs.filter(track_filter)
        eval_map = get_evaluations_for_papers(list(papers_qs))
    else:
        eval_map = get_evaluations_for_papers(list(papers_qs))

    locks_map = get_locks_map(active_schedule, day=day)
    rows = build_evaluation_report_rows(
        list(papers_qs.order_by('day', 'track_session', 'serial_order')),
        eval_map,
        locks_map=locks_map,
    )
    buffer = generate_evaluation_report_workbook(rows)
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="ICRAET2026_Evaluation_Report.xlsx"'
    return response


@admin_required
@require_http_methods(['POST'])
def upload_verifier_assignments(request):
    uploaded_file = request.FILES.get('verifier_file')
    if not uploaded_file:
        return JsonResponse({'success': False, 'error': 'Please select a track duty Excel with VERIFIER column.'}, status=400)

    active_schedule = _get_active_schedule()
    if not active_schedule:
        return JsonResponse({'success': False, 'error': 'Upload conference schedule first.'}, status=400)

    try:
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            for chunk in uploaded_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        assignments = parse_verifier_assignments(tmp_path)
        os.unlink(tmp_path)

        if not assignments:
            return JsonResponse({'success': False, 'error': 'No verifier data found. Check VERIFIER column in Day sheets.'}, status=400)

        updated = apply_verifier_assignments(active_schedule, assignments)
        verifier_profiles = sync_verifier_users(active_schedule)

        return JsonResponse({
            'success': True,
            'message': f'Assigned verifiers to {updated} track rows. Created {len(verifier_profiles)} verifier logins.',
            'updated': updated,
            'verifier_count': len(verifier_profiles),
        })
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=500)


@admin_required
def moderator_credentials_page(request):
    active_schedule = _get_active_schedule()
    rows = build_moderator_credential_rows(active_schedule) if active_schedule else []
    context = {
        'page_title': 'Moderator-2 Credentials',
        'page_subtitle': 'Login details, contact info & email for Moderator-2 (Entry)',
        'rows': rows,
        'stats': credential_stats(rows) if rows else {
            'total_rows': 0, 'unique_people': 0, 'with_email': 0, 'without_email': 0,
        },
        'download_url': reverse('download_faculty_credentials'),
        'send_email_url': reverse('send_moderator_credentials_email'),
        'empty_message': 'No Moderator-2 credentials. Upload schedule Excel first.',
        'sidebar_active': 'credentials',
        'is_admin': True,
    }
    return render(request, 'marksheet/credentials_page.html', context)


@admin_required
def verifier_credentials_page(request):
    active_schedule = _get_active_schedule()
    rows = build_verifier_credential_rows(active_schedule) if active_schedule else []
    context = {
        'page_title': 'Verifier Credentials',
        'page_subtitle': 'Login details, contact info & email for Verifiers',
        'rows': rows,
        'stats': credential_stats(rows) if rows else {
            'total_rows': 0, 'unique_people': 0, 'with_email': 0, 'without_email': 0,
        },
        'download_url': reverse('download_verifier_credentials'),
        'send_email_url': reverse('send_verifier_credentials_email'),
        'empty_message': 'No verifier credentials. Upload verifier assignment Excel first.',
        'sidebar_active': 'verifier_credentials',
        'is_admin': True,
    }
    return render(request, 'marksheet/credentials_page.html', context)


@admin_required
@require_http_methods(['POST'])
def send_moderator_credentials_email(request):
    active_schedule = _get_active_schedule()
    if not active_schedule:
        return JsonResponse({'success': False, 'error': 'No schedule uploaded.'}, status=400)

    recipients = group_moderator_email_recipients(active_schedule)
    if not recipients:
        return JsonResponse({'success': False, 'error': 'No Moderator-2 credentials found.'}, status=400)

    login_url = request.build_absolute_uri(reverse('login'))
    if not login_url.startswith('http'):
        login_url = f"{settings.SITE_URL}{reverse('login')}"

    result = send_credential_emails(recipients, login_url)
    return JsonResponse({
        'success': True,
        'sent': result['sent'],
        'skipped_no_email': result['skipped_no_email'],
        'failed': result['failed'],
    })


@admin_required
@require_http_methods(['POST'])
def send_verifier_credentials_email(request):
    active_schedule = _get_active_schedule()
    if not active_schedule:
        return JsonResponse({'success': False, 'error': 'No schedule uploaded.'}, status=400)

    recipients = group_verifier_email_recipients(active_schedule)
    if not recipients:
        return JsonResponse({'success': False, 'error': 'No verifier credentials found.'}, status=400)

    login_url = request.build_absolute_uri(reverse('login'))
    if not login_url.startswith('http'):
        login_url = f"{settings.SITE_URL}{reverse('login')}"

    result = send_credential_emails(recipients, login_url)
    return JsonResponse({
        'success': True,
        'sent': result['sent'],
        'skipped_no_email': result['skipped_no_email'],
        'failed': result['failed'],
    })


@admin_required
def download_verifier_credentials(request):
    active_schedule = _get_active_schedule()
    if not active_schedule:
        return HttpResponse('No schedule uploaded.', status=404)

    profiles = list(get_verifier_profiles(active_schedule))
    if not profiles:
        return HttpResponse('No verifier credentials. Upload verifier assignment Excel first.', status=404)

    buffer = generate_verifier_credentials_workbook(profiles)
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="ICRAET2026_Verifier_Credentials.xlsx"'
    return response


@verifier_login_required
def verifier_dashboard(request):
    profile = request.user.verifier_profile
    active_schedule = _get_active_schedule() or profile.schedule
    selected_day = request.GET.get('day')
    try:
        selected_day = int(selected_day) if selected_day else None
    except ValueError:
        selected_day = None

    duties = get_verifier_duties(profile, schedule=active_schedule, day=selected_day)
    locks = get_locks_map(active_schedule, day=selected_day) if active_schedule else {}

    duty_items = []
    for item in duties:
        duty = item['duty']
        lock = locks.get((duty.day, duty.track_session))
        duty_items.append({
            'duty': duty,
            'roles': item['roles'],
            'is_locked': bool(lock and lock.is_locked),
            'locked_at': lock.locked_at if lock else None,
        })

    days = sorted(set(
        TrackDuty.objects.filter(schedule=active_schedule).exclude(verifier='').values_list('day', flat=True)
    )) if active_schedule else []

    context = {
        'profile': profile,
        'duties': duty_items,
        'days': days,
        'selected_day': selected_day,
        'active_schedule': active_schedule,
        'sidebar_active': 'duties',
    }
    return render(request, 'marksheet/verifier_dashboard.html', context)


@verifier_login_required
def verifier_evaluations(request):
    profile = request.user.verifier_profile
    active_schedule = _get_active_schedule() or profile.schedule
    track_keys = get_verifier_track_keys(profile, schedule=active_schedule)
    track_key = request.GET.get('track')

    track_options = []
    papers = []
    selected_track = None
    track_locked = False
    lock_info = None

    if active_schedule and track_keys:
        all_papers = Paper.objects.filter(schedule=active_schedule)
        locks = get_locks_map(active_schedule)
        for day, track_session in sorted(track_keys):
            key = f'{day}|{track_session}'
            count = all_papers.filter(day=day, track_session=track_session).count()
            sample = all_papers.filter(day=day, track_session=track_session).first()
            track_name = sample.track_name if sample else ''
            lk = locks.get((day, track_session))
            locked_label = ' [LOCKED]' if lk and lk.is_locked else ''
            track_options.append({
                'key': key,
                'label': _format_track_option_label(
                    day, track_session, track_name, count, locked_label
                ),
            })

        if track_key and '|' in track_key:
            day_str, track_session = track_key.split('|', 1)
            try:
                day = int(day_str)
            except ValueError:
                day = None
            if day and (day, track_session) in track_keys:
                papers = list(
                    all_papers.filter(day=day, track_session=track_session)
                    .order_by('serial_order')
                )
                selected_track = track_key
                evaluations = get_evaluations_for_papers(papers)
                lock_info = locks.get((day, track_session))
                track_locked = bool(lock_info and lock_info.is_locked)
                for paper in papers:
                    paper.user_evaluation = evaluations.get(paper.id)
                    paper.eval_status = (
                        'Completed' if paper.user_evaluation and paper.user_evaluation.is_complete
                        else 'Pending'
                    )

    context = {
        'profile': profile,
        'track_options': track_options,
        'selected_track': selected_track,
        'papers': papers,
        'track_locked': track_locked,
        'lock_info': lock_info,
        'sidebar_active': 'evaluations',
    }
    return render(request, 'marksheet/verifier_evaluations.html', context)


@verifier_login_required
@require_http_methods(['POST'])
def lock_track_session(request):
    track_key = request.POST.get('track')
    if not track_key or '|' not in track_key:
        return JsonResponse({'success': False, 'error': 'Invalid track.'}, status=400)

    day_str, track_session = track_key.split('|', 1)
    try:
        day = int(day_str)
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid day.'}, status=400)

    profile = request.user.verifier_profile
    active_schedule = _get_active_schedule() or profile.schedule
    track_keys = get_verifier_track_keys(profile, schedule=active_schedule, day=day)
    if (day, track_session) not in track_keys:
        return JsonResponse({'success': False, 'error': 'Not your assigned track.'}, status=403)

    lock_track(active_schedule, day, track_session, request.user)
    return redirect(f"{reverse('verifier_evaluations')}?track={day}|{track_session}")


@admin_required
def download_faculty_credentials(request):
    active_schedule = _get_active_schedule()
    if not active_schedule:
        return HttpResponse('No schedule uploaded.', status=404)

    profiles = list(get_moderator2_profiles(active_schedule))
    if not profiles:
        return HttpResponse('No faculty credentials found. Upload schedule first.', status=404)

    buffer = generate_credentials_workbook(profiles)
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="ICRAET2026_Faculty_Credentials.xlsx"'
    return response


@admin_required
@require_http_methods(['POST'])
def upload_schedule(request):
    uploaded_file = request.FILES.get('schedule_file')
    if not uploaded_file:
        return JsonResponse({'success': False, 'error': 'Please select an Excel file.'}, status=400)

    if not uploaded_file.name.lower().endswith(('.xlsx', '.xls')):
        return JsonResponse({'success': False, 'error': 'Only .xlsx files are supported.'}, status=400)

    try:
        with transaction.atomic():
            active_schedule = ScheduleUpload.objects.filter(is_active=True).first()
            reupload = active_schedule is not None

            if reupload:
                schedule = active_schedule
                schedule.file.save(uploaded_file.name, uploaded_file, save=False)
            else:
                schedule = ScheduleUpload(file=uploaded_file, is_active=True)

            schedule.save()

            parsed_papers, tracks = parse_schedule_file(schedule.file.path)
            duty_by_day = parse_track_duty(schedule.file.path)

            if reupload:
                paper_stats = sync_papers(schedule, parsed_papers)
                sync_track_duties(schedule, duty_by_day, preserve_verifier=True)
                faculty_profiles = sync_faculty_users(
                    schedule, duty_by_day, preserve_existing=True
                )
                message = (
                    f'Schedule updated: {paper_stats["total"]} papers '
                    f'({paper_stats["unchanged"]} unchanged, {paper_stats["updated"]} updated, '
                    f'{paper_stats["created"]} new, {paper_stats["removed"]} removed). '
                    f'{paper_stats["evaluations_preserved"]} evaluation(s) preserved. '
                    f'{len(faculty_profiles)} Moderator-2 login(s) active.'
                )
            else:
                Paper.objects.bulk_create([
                    Paper(schedule=schedule, **paper_data)
                    for paper_data in parsed_papers
                ])
                sync_track_duties(schedule, duty_by_day, preserve_verifier=False)
                faculty_profiles = sync_faculty_users(
                    schedule, duty_by_day, preserve_existing=False
                )
                paper_stats = {'total': len(parsed_papers), 'evaluations_preserved': 0}
                message = (
                    f'Successfully imported {len(parsed_papers)} papers from {len(tracks)} track sessions. '
                    f'Created {len(faculty_profiles)} Moderator-2 logins.'
                )

            schedule.total_papers = Paper.objects.filter(schedule=schedule).count()
            schedule.total_tracks = len(tracks)
            schedule.save()

        return JsonResponse({
            'success': True,
            'message': message,
            'total_papers': schedule.total_papers,
            'total_tracks': len(tracks),
            'faculty_count': len(faculty_profiles),
            'reupload': reupload,
            'paper_stats': paper_stats,
        })
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=500)


@admin_required
@require_http_methods(['POST'])
def upload_template(request):
    uploaded_file = request.FILES.get('template_file')
    if not uploaded_file:
        return JsonResponse({'success': False, 'error': 'Please select an Excel template file.'}, status=400)

    if not uploaded_file.name.lower().endswith('.xlsx'):
        return JsonResponse({'success': False, 'error': 'Only .xlsx template files are supported.'}, status=400)

    if uploaded_file.size > 5 * 1024 * 1024:
        return JsonResponse({'success': False, 'error': 'Template file is too large (max 5 MB).'}, status=400)

    try:
        templates_dir = Path(settings.MEDIA_ROOT) / 'templates'
        templates_dir.mkdir(parents=True, exist_ok=True)

        from openpyxl import load_workbook

        uploaded_file.seek(0)
        workbook = load_workbook(uploaded_file, read_only=True)
        workbook.close()
        uploaded_file.seek(0)

        template = MarksheetTemplate(
            file=uploaded_file,
            name=uploaded_file.name,
            is_active=True,
        )
        template.save()
        return JsonResponse({
            'success': True,
            'message': f'Marksheet template "{template.name}" uploaded successfully.',
            'template_name': template.name,
        })
    except Exception as exc:
        return JsonResponse({'success': False, 'error': f'Upload failed: {exc}'}, status=500)


@admin_required
def download_track_marksheets(request):
    track_key = request.GET.get('track')
    if not track_key:
        return HttpResponse('Track not selected.', status=400)

    try:
        day, track_session = track_key.split('|', 1)
        day = int(day)
    except ValueError:
        return HttpResponse('Invalid track selection.', status=400)

    active_schedule = _get_active_schedule()
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


@admin_required
def download_day_marksheets(request):
    day = request.GET.get('day')
    if not day:
        return HttpResponse('Day not selected.', status=400)

    try:
        day = int(day)
    except ValueError:
        return HttpResponse('Invalid day selection.', status=400)

    active_schedule = _get_active_schedule()
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


@admin_required
def download_all_marksheets(request):
    active_schedule = _get_active_schedule()
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


@admin_required
def download_track_duty(request):
    day = request.GET.get('day')
    active_schedule = _get_active_schedule()
    if not active_schedule:
        return HttpResponse('No schedule uploaded.', status=404)

    duty_by_day = parse_track_duty(active_schedule.file.path)
    if not duty_by_day:
        return HttpResponse('No track duty data found in schedule.', status=404)

    if day:
        try:
            day = int(day)
        except ValueError:
            return HttpResponse('Invalid day selection.', status=400)
        if day not in duty_by_day:
            return HttpResponse('No track duty data for this day.', status=404)
        days = [day]
        filename = f'ICRAET2026_Track_Duty_Day{day}.xlsx'
    else:
        days = sorted(duty_by_day.keys())
        filename = 'ICRAET2026_Track_Duty_All_Days.xlsx'

    buffer = generate_track_duty_workbook(duty_by_day, days=days)
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
