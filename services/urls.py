from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_redirect, name='dashboard'),
    path('provider/', views.provider_dashboard, name='provider_dashboard'),
    path('worker/', views.worker_dashboard, name='worker_dashboard'),
    path('find/', views.find_jobs, name='find_jobs'),
    path('post/', views.post_job, name='post_job'),
    path('post/new/', views.post_job_page, name='post_job_page'),
    path('<int:job_id>/accept/', views.accept_job, name='accept_job'),
    path('<int:job_id>/update_status/', views.update_status, name='update_status'),
    path('<int:job_id>/update_location/', views.update_location, name='update_location'),
    path('<int:job_id>/get_location/', views.get_location, name='get_location'),
    path('map/', views.nearby_map, name='nearby_map'),
    path('<int:job_id>/track/', views.job_tracking, name='job_tracking'),
    path('request/send/<int:worker_id>/', views.send_service_request, name='send_service_request'),
    path('request/<int:request_id>/respond/', views.respond_service_request, name='respond_service_request'),
    path('job/<int:job_id>/assign/<int:worker_id>/', views.assign_job_to_worker, name='assign_job_to_worker'),
    path('application/<int:application_id>/respond/', views.respond_job_application, name='respond_job_application'),
]
