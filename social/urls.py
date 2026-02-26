from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('network/', views.network_view, name='network'),
    path('jobs/', views.jobs_view, name='jobs'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/mark-read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('notifications/<int:notification_id>/view/', views.mark_notification_read_and_redirect, name='notification_redirect'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('profile/toggle-availability/', views.toggle_availability, name='toggle_availability'),
    path('profile/update-skills/', views.update_skills, name='update_skills'),
    path('business/', views.business_view, name='business'),
    path('test-login/', views.test_login_view, name='test_login'),
    path('user/<int:user_id>/', views.user_profile_view, name='user_profile'),
    path('connect/<int:user_id>/', views.send_connection, name='send_connection'),
    path('connect/<int:user_id>/accept/', views.accept_connection, name='accept_connection'),
    path('connect/<int:user_id>/reject/', views.reject_connection, name='reject_connection'),
    path('connect/<int:user_id>/cancel/', views.cancel_connection, name='cancel_connection'),
]
