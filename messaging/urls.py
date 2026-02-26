from django.urls import path
from . import views

urlpatterns = [
    path('', views.inbox_view, name='inbox'),
    path('fetch/<int:user_id>/', views.fetch_chat, name='fetch_chat'),
    path('send/<int:user_id>/', views.send_message, name='send_message'),
]
