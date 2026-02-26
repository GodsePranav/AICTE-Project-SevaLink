import math
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Prefetch

from accounts.models import Profile, CustomUser
from social.models import Post, Comment, Like

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance in kilometers between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371 # Radius of earth in kilometers
    return c * r

@api_view(['GET'])
@permission_classes([AllowAny])
def nearby_workers_api(request):
    try:
        user_lat = float(request.GET.get('lat'))
        user_lng = float(request.GET.get('lng'))
        radius_km = float(request.GET.get('radius', 10))
    except (TypeError, ValueError):
        return Response({"error": "Valid lat and lng are required."}, status=status.HTTP_400_BAD_REQUEST)

    # Fetch workers (Professional or Trade-Skills)
    workers = Profile.objects.filter(
        user_type__in=['Professional', 'Trade-Skills'],
        latitude__isnull=False,
        longitude__isnull=False
    ).select_related('user')

    nearby_workers = []
    for profile in workers:
        distance = haversine(user_lat, user_lng, profile.latitude, profile.longitude)
        if distance <= radius_km:
            nearby_workers.append({
                'id': profile.user.id,
                'username': profile.user.username,
                'user_type': profile.user_type,
                'is_verified': profile.is_verified,
                'latitude': profile.latitude,
                'longitude': profile.longitude,
                'distance_km': round(distance, 2),
                'service_skills': profile.service_skills,
            })

    # Sort by distance
    nearby_workers.sort(key=lambda x: x['distance_km'])
    
    return Response({'workers': nearby_workers})

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def feed_api(request):
    if request.method == 'GET':
        posts = Post.objects.select_related('author').prefetch_related(
            'comments__author', 'likes'
        ).order_by('-timestamp')[:50] # Get latest 50 posts
        
        feed_data = []
        for post in posts:
            feed_data.append({
                'id': post.id,
                'author': post.author.username,
                'author_id': post.author.id,
                'text_content': post.text_content,
                'image_url': post.image_upload.url if post.image_upload else None,
                'voice_url': post.voice_upload.url if post.voice_upload else None,
                'timestamp': post.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'likes_count': post.likes.count(),
                'has_liked': post.likes.filter(user=request.user).exists(),
                'comments': [
                    {
                        'id': c.id,
                        'author': c.author.username,
                        'text_content': c.text_content,
                        'timestamp': c.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    } for c in post.comments.all()
                ]
            })
            
        return Response({'posts': feed_data})

    elif request.method == 'POST':
        text_content = request.data.get('text_content', '')
        image_upload = request.FILES.get('image_upload')
        voice_upload = request.FILES.get('voice_upload')
        
        if not text_content and not image_upload and not voice_upload:
            return Response({"error": "Post must not be empty."}, status=status.HTTP_400_BAD_REQUEST)
            
        post = Post.objects.create(
            author=request.user,
            text_content=text_content,
            image_upload=image_upload,
            voice_upload=voice_upload
        )
        
        return Response({"id": post.id, "message": "Post created successfully"}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def like_post_api(request, post_id):
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)
        
    like, created = Like.objects.get_or_create(post=post, user=request.user)
    
    if not created:
        like.delete()
        return Response({"message": "Post unliked", "liked": False, "likes_count": post.likes.count()})
        
    return Response({"message": "Post liked", "liked": True, "likes_count": post.likes.count()})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def comment_post_api(request, post_id):
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)
        
    text_content = request.data.get('text_content', '')
    if not text_content:
        return Response({"error": "Comment cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)
        
    comment = Comment.objects.create(post=post, author=request.user, text_content=text_content)
    return Response({
        "id": comment.id, 
        "author": request.user.username,
        "text_content": comment.text_content,
        "timestamp": comment.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    }, status=status.HTTP_201_CREATED)
