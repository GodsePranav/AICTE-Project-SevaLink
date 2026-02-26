from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib import messages as django_messages
from .models import Post, Job, Notification, ConnectionRequest
from services.models import ServiceJob


def home_view(request):
    if not request.user.is_authenticated:
        return render(request, 'home.html', {})

    from services.models import ServiceJob
    context = {}
    
    # Determine sort order from query parameter
    sort_param = request.GET.get('sort', 'newest')
    sort_map = {
        'newest': '-created_at',
        'oldest': 'created_at',
        'price_high': '-price',
        'price_low': 'price',
    }
    order = sort_map.get(sort_param, '-created_at')
    
    try:
        role = request.user.profile.role
        if role == 'Job Provider':
            context['active_jobs'] = ServiceJob.objects.filter(provider=request.user).exclude(status__in=['Completed', 'Cancelled']).order_by(order)
        if role == 'Worker':
            context['available_jobs'] = ServiceJob.objects.filter(status='Pending', worker__isnull=True).order_by(order)
    except Exception:
        pass

    return render(request, 'home.html', context)


@login_required
def network_view(request):
    """LinkedIn-style network page showing all profiles with connect/search."""
    from django.contrib.auth import get_user_model
    from django.db.models import Q
    User = get_user_model()

    search_query = request.GET.get('q', '').strip()
    active_tab = request.GET.get('tab', 'all')

    # Get all users except current user
    users = User.objects.exclude(id=request.user.id).select_related('profile').order_by('-date_joined')

    # Search filter
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(profile__service_skills__icontains=search_query) |
            Q(profile__job_title__icontains=search_query) |
            Q(profile__role__icontains=search_query)
        ).distinct()

    # Build connection status for each user
    my_profile = request.user.profile
    my_connections = set(my_profile.connections.values_list('user_id', flat=True))

    # Pending requests I sent
    sent_pending = set(ConnectionRequest.objects.filter(
        from_user=request.user, status='pending'
    ).values_list('to_user_id', flat=True))

    # Pending requests I received
    received_pending = set(ConnectionRequest.objects.filter(
        to_user=request.user, status='pending'
    ).values_list('from_user_id', flat=True))

    # Incoming connection requests (for notification area)
    incoming_requests = ConnectionRequest.objects.filter(
        to_user=request.user, status='pending'
    ).select_related('from_user', 'from_user__profile').order_by('-timestamp')

    # Annotate users with connection status
    user_list = []
    connected_list = []
    for u in users:
        profile = getattr(u, 'profile', None)
        if not profile:
            continue
        if u.id in my_connections:
            conn_status = 'connected'
        elif u.id in sent_pending:
            conn_status = 'pending_sent'
        elif u.id in received_pending:
            conn_status = 'pending_received'
        else:
            conn_status = 'none'
        item = {
            'user': u,
            'profile': profile,
            'connection_status': conn_status,
        }
        user_list.append(item)
        if conn_status == 'connected':
            connected_list.append(item)

    # Pick which list to display based on tab
    display_users = connected_list if active_tab == 'connections' else user_list

    context = {
        'users': user_list,
        'display_users': display_users,
        'search_query': search_query,
        'connection_count': len(my_connections),
        'incoming_requests': incoming_requests,
        'total_users': len(user_list),
        'active_tab': active_tab,
    }
    return render(request, 'network.html', context)


@login_required
@require_POST
def send_connection(request, user_id):
    """Send a connection request."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    target_user = get_object_or_404(User, id=user_id)

    if target_user == request.user:
        return JsonResponse({'error': 'Cannot connect with yourself'}, status=400)

    # Check if already connected
    if request.user.profile.connections.filter(user_id=target_user.id).exists():
        return JsonResponse({'error': 'Already connected'}, status=400)

    # Check if request already exists
    existing = ConnectionRequest.objects.filter(from_user=request.user, to_user=target_user).first()
    if existing:
        return JsonResponse({'error': 'Request already sent'}, status=400)

    # Check if they sent us a request — auto-accept
    reverse_req = ConnectionRequest.objects.filter(from_user=target_user, to_user=request.user, status='pending').first()
    if reverse_req:
        reverse_req.status = 'accepted'
        reverse_req.save()
        request.user.profile.connections.add(target_user.profile)
        target_user.profile.connections.add(request.user.profile)
        Notification.objects.create(user=target_user, actor=request.user.username, verb='accepted your connection request')
        return JsonResponse({'status': 'ok', 'result': 'connected'})

    ConnectionRequest.objects.create(from_user=request.user, to_user=target_user)
    Notification.objects.create(user=target_user, actor=f"{request.user.first_name or request.user.username} {request.user.last_name}".strip(), verb='sent you a connection request')
    return JsonResponse({'status': 'ok', 'result': 'pending_sent'})


@login_required
@require_POST
def accept_connection(request, user_id):
    """Accept a connection request."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    from_user = get_object_or_404(User, id=user_id)

    conn_req = get_object_or_404(ConnectionRequest, from_user=from_user, to_user=request.user, status='pending')
    conn_req.status = 'accepted'
    conn_req.save()

    # Add mutual connection
    request.user.profile.connections.add(from_user.profile)
    from_user.profile.connections.add(request.user.profile)

    Notification.objects.create(user=from_user, actor=f"{request.user.first_name or request.user.username} {request.user.last_name}".strip(), verb='accepted your connection request')
    return JsonResponse({'status': 'ok', 'result': 'connected'})


@login_required
@require_POST
def reject_connection(request, user_id):
    """Reject a connection request."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    from_user = get_object_or_404(User, id=user_id)

    conn_req = get_object_or_404(ConnectionRequest, from_user=from_user, to_user=request.user, status='pending')
    conn_req.status = 'rejected'
    conn_req.save()
    return JsonResponse({'status': 'ok', 'result': 'rejected'})


@login_required
@require_POST
def cancel_connection(request, user_id):
    """Withdraw a connection request sent by current user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    to_user = get_object_or_404(User, id=user_id)

    # Find and delete the pending request sent by this user
    try:
        conn_req = ConnectionRequest.objects.get(from_user=request.user, to_user=to_user, status='pending')
        conn_req.delete()
        return JsonResponse({'status': 'ok', 'result': 'cancelled'})
    except ConnectionRequest.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Request not found'}, status=404)

@login_required
def user_profile_view(request, user_id):
    """View another user's detailed profile."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    target_user = get_object_or_404(User, id=user_id)
    
    # Check connection status
    my_profile = request.user.profile
    connection_status = 'none'
    
    if my_profile.connections.filter(user=target_user).exists():
        connection_status = 'connected'
    elif ConnectionRequest.objects.filter(from_user=request.user, to_user=target_user, status='pending').exists():
        connection_status = 'pending_sent'
    elif ConnectionRequest.objects.filter(from_user=target_user, to_user=request.user, status='pending').exists():
        connection_status = 'pending_received'
        
    context = {
        'target_user': target_user,
        'connection_status': connection_status,
    }
    return render(request, 'user_profile.html', context)



@login_required
def jobs_view(request):
    """Show available worker profiles that job providers can browse and hire."""
    from django.contrib.auth import get_user_model
    from django.db.models import Q
    from accounts.models import Profile
    User = get_user_model()

    filter_skill = request.GET.get('filter', '').strip()
    search_query = request.GET.get('q', '').strip()

    # Get all workers (role=Worker)
    workers = Profile.objects.filter(
        role='Worker',
    ).exclude(user=request.user).select_related('user').order_by('-user__date_joined')

    # Skill filter from quick-filter buttons
    if filter_skill:
        workers = workers.filter(
            Q(service_skills__icontains=filter_skill) |
            Q(job_title__icontains=filter_skill) |
            Q(primary_category__icontains=filter_skill)
        )

    # Search filter
    if search_query:
        workers = workers.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(service_skills__icontains=search_query) |
            Q(job_title__icontains=search_query) |
            Q(full_name__icontains=search_query)
        ).distinct()

    # If user is a provider, include their pending jobs for the "Ask to do Task" dropdown
    provider_jobs = []
    if hasattr(request.user, 'profile') and request.user.profile.role == 'Job Provider':
        from services.models import ServiceJob
        provider_jobs = ServiceJob.objects.filter(
            provider=request.user, status='Pending', worker__isnull=True
        ).order_by('-created_at')

    context = {
        'workers': workers,
        'current_filter': filter_skill,
        'search_query': search_query,
        'total_workers': workers.count(),
        'provider_jobs': provider_jobs,
    }
    return render(request, 'find_workers.html', context)


@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-timestamp')
    return render(request, 'notifications.html', {'notifications': notifications})


@login_required
@require_POST
def mark_notifications_read(request):
    """Mark all notifications as read for the current user."""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'ok', 'message': 'All notifications marked as read'})


@login_required
def mark_notification_read_and_redirect(request, notification_id):
    """Mark a specific notification as read and redirect to its URL."""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    
    url = notification.redirect_url
    if url:
        # Avoid circular redirect if the url is 'notifications'
        if url == 'notifications':
             return redirect('notifications')
             
        # If it's a relative URL without a leading slash and not a known named URL
        from django.urls import resolve, Resolver404
        try:
            # Check if it's already a valid path
            resolve(url if url.startswith('/') else '/' + url)
            if not url.startswith('/') and not url.startswith('http'):
                url = '/' + url
        except Resolver404:
            # Maybe it's a named URL?
            try:
                from django.urls import reverse
                url = reverse(url)
            except:
                pass
                
        return redirect(url)
    return redirect('notifications')


@login_required
@require_POST
def toggle_availability(request):
    """Toggle the user's is_available status via AJAX."""
    profile = request.user.profile
    profile.is_available = not profile.is_available
    profile.save(update_fields=['is_available'])
    return JsonResponse({
        'status': 'ok',
        'is_available': profile.is_available,
    })


@login_required
@require_POST
def update_skills(request):
    """Update the user's service_skills from the profile page via AJAX."""
    import json
    try:
        data = json.loads(request.body)
        skills = data.get('skills', '').strip()
    except (json.JSONDecodeError, AttributeError):
        skills = request.POST.get('skills', '').strip()
    
    profile = request.user.profile
    profile.service_skills = skills
    profile.save(update_fields=['service_skills'])
    return JsonResponse({
        'status': 'ok',
        'skills': profile.service_skills,
    })


@login_required
def profile_view(request):
    profile = getattr(request.user, 'profile', None)
    # Count jobs
    jobs_posted = ServiceJob.objects.filter(provider=request.user).count()
    jobs_completed = ServiceJob.objects.filter(
        provider=request.user, status='Completed'
    ).count() + ServiceJob.objects.filter(
        worker=request.user, status='Completed'
    ).count()

    context = {
        'profile': profile,
        'jobs_posted': jobs_posted,
        'jobs_completed': jobs_completed,
    }
    return render(request, 'profile.html', context)


@login_required
def edit_profile_view(request):
    from accounts.forms import UserEditForm, ProfileEditForm

    if request.method == 'POST':
        user_form = UserEditForm(instance=request.user, data=request.POST)
        profile_form = ProfileEditForm(instance=request.user.profile, data=request.POST, files=request.FILES)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            django_messages.success(request, 'Your profile has been updated successfully.')
            return redirect('profile')
        else:
            django_messages.error(request, 'Error updating your profile. Please check the fields.')
    else:
        user_form = UserEditForm(instance=request.user)
        profile_form = ProfileEditForm(instance=request.user.profile)

    return render(request, 'edit_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })


@login_required
def business_view(request):
    """Dashboard with real job data and availability toggle."""
    profile = getattr(request.user, 'profile', None)
    active_jobs = ServiceJob.objects.filter(
        provider=request.user
    ).exclude(status__in=['Completed', 'Cancelled']).count()

    total_jobs = ServiceJob.objects.filter(provider=request.user).count()

    context = {
        'active_jobs': active_jobs,
        'total_jobs': total_jobs,
        'is_available': profile.is_available if profile else True,
    }
    return render(request, 'business.html', context)


def test_login_view(request):
    from django.contrib.auth import get_user_model, login
    User = get_user_model()
    user, created = User.objects.get_or_create(username='testprovider')
    if created:
        user.set_password('testpass123')
        user.save()
        from accounts.models import Profile
        Profile.objects.create(user=user, role='Job Provider')

    login(request, user)
    return redirect('home')
