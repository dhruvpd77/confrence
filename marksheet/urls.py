from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path('', views.AdminLoginView.as_view(), name='login'),
    path('faculty/login/', views.AdminLoginView.as_view(), name='faculty_login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),

    path('dashboard/', views.dashboard, name='dashboard'),
    path('faculty/', views.faculty_dashboard, name='faculty_dashboard'),
    path('faculty/evaluations/', views.faculty_evaluations, name='faculty_evaluations'),

    path('verifier/', views.verifier_dashboard, name='verifier_dashboard'),
    path('verifier/evaluations/', views.verifier_evaluations, name='verifier_evaluations'),
    path('verifier/lock/', views.lock_track_session, name='lock_track_session'),

    path('evaluations/', views.admin_evaluations, name='admin_evaluations'),
    path('evaluations/<int:paper_id>/', views.evaluation_form, name='evaluation_form'),
    path('reports/', views.evaluation_report, name='evaluation_report'),
    path('results/', views.results_ranking, name='results_ranking'),

    path('upload/', views.upload_schedule, name='upload_schedule'),
    path('upload/template/', views.upload_template, name='upload_template'),
    path('upload/verifier/', views.upload_verifier_assignments, name='upload_verifier_assignments'),
    path('download/track/', views.download_track_marksheets, name='download_track'),
    path('download/day/', views.download_day_marksheets, name='download_day'),
    path('download/all/', views.download_all_marksheets, name='download_all'),
    path('download/track-duty/', views.download_track_duty, name='download_track_duty'),
    path('credentials/moderator/', views.moderator_credentials_page, name='moderator_credentials'),
    path('credentials/verifier/', views.verifier_credentials_page, name='verifier_credentials'),
    path('credentials/moderator/send-email/', views.send_moderator_credentials_email, name='send_moderator_credentials_email'),
    path('credentials/verifier/send-email/', views.send_verifier_credentials_email, name='send_verifier_credentials_email'),
    path('credentials/update-contact/', views.update_credential_contact, name='update_credential_contact'),
    path('download/credentials/', views.download_faculty_credentials, name='download_faculty_credentials'),
    path('download/verifier-credentials/', views.download_verifier_credentials, name='download_verifier_credentials'),
    path('download/evaluation-report/', views.download_evaluation_report, name='download_evaluation_report'),
]
