from django.urls import path
from . import views

urlpatterns = [
    path('nearby/', views.nearby_workers_api, name='nearby_workers_api'),
    path('feed/', views.feed_api, name='feed_api'),
    path('feed/post/<int:post_id>/like/', views.like_post_api, name='like_post_api'),
    path('feed/post/<int:post_id>/comment/', views.comment_post_api, name='comment_post_api'),
]
