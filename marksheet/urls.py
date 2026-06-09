from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path('', views.AdminLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('upload/', views.upload_schedule, name='upload_schedule'),
    path('upload/template/', views.upload_template, name='upload_template'),
    path('download/track/', views.download_track_marksheets, name='download_track'),
    path('download/day/', views.download_day_marksheets, name='download_day'),
    path('download/all/', views.download_all_marksheets, name='download_all'),
]
