from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import ServiceJob, JobTracking, ServiceRequest, JobApplication, Review
from social.models import Notification
from django.views.decorators.http import require_POST
from django.contrib import messages
import json

# ... existing views ...

@login_required
@require_POST
def send_service_request(request, worker_id):
    """Job Provider sends a request to a Worker to do a task."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    worker = get_object_or_404(User, id=worker_id)
    
    if request.user.profile.role != 'Job Provider':
        return JsonResponse({'error': 'Only Job Providers can send task requests.'}, status=403)
    
    # Get job_id from POST data (if linking to a specific job)
    job_id = request.POST.get('job_id') or json.loads(request.body).get('job_id') if request.body else None
    job = None
    if job_id:
        job = get_object_or_404(ServiceJob, id=job_id, provider=request.user)
    
    # Create the service request with the job link
    service_req, created = ServiceRequest.objects.get_or_create(
        provider=request.user,
        worker=worker,
        job=job,
        defaults={'status': 'pending'}
    )
    if not created and service_req.status != 'pending':
        service_req.status = 'pending'
        service_req.save()
        
    job_info = f' for "{job.title}"' if job else ''
    Notification.objects.create(
        user=worker,
        actor=f"{request.user.first_name or request.user.username} {request.user.last_name}".strip(),
        verb=f'invited you to do a task{job_info}',
        target=job.title if job else None,
        redirect_url='/services/worker/'
    )
    
    return JsonResponse({'status': 'ok', 'message': 'Request sent to worker.'})

@login_required
@require_POST
def respond_service_request(request, request_id):
    """Worker accepts or rejects a service request."""
    service_req = get_object_or_404(ServiceRequest, id=request_id, worker=request.user)
    action = request.POST.get('action') # 'accepted' or 'rejected'
    
    if action not in ['accepted', 'rejected']:
        return JsonResponse({'error': 'Invalid action'}, status=400)
    
    service_req.status = action
    service_req.save()
    
    if action == 'accepted' and service_req.job:
        job = service_req.job
        if job.status == 'Pending' and job.worker is None:
            job.worker = request.user
            job.status = 'Accepted'
            job.save()
            
            Notification.objects.create(
                user=service_req.provider,
                actor=f"{request.user.first_name or request.user.username} {request.user.last_name}".strip(),
                verb='accepted your task invitation and is assigned to:',
                target=job.title,
                redirect_url=f"/messages/?user={request.user.id}"
            )
            
            messages.success(request, f'You accepted the job "{job.title}"! It\'s now in your dashboard.')
        else:
            messages.info(request, 'You accepted the invitation, but the job is no longer available.')
    elif action == 'accepted':
        Notification.objects.create(
            user=service_req.provider,
            actor=f"{request.user.first_name or request.user.username} {request.user.last_name}".strip(),
            verb='accepted your task invitation. You can now message them.',
            redirect_url=f"/messages/?user={request.user.id}"
        )
        messages.success(request, 'You accepted the invitation! The provider has been notified.')
    else:
        Notification.objects.create(
            user=service_req.provider,
            actor=f"{request.user.first_name or request.user.username} {request.user.last_name}".strip(),
            verb='declined your task invitation',
            redirect_url='/services/provider/'
        )
        messages.info(request, 'You declined the invitation.')
    
    return redirect('worker_dashboard')

@login_required
@require_POST
def withdraw_service_request(request, request_id):
    """Job Provider withdraws a pending service request before it is accepted."""
    service_req = get_object_or_404(ServiceRequest, id=request_id, provider=request.user)
    
    if service_req.status != 'pending':
        return JsonResponse({'error': 'Can only withdraw pending requests.'}, status=400)
        
    service_req.delete()
    return JsonResponse({'status': 'ok', 'message': 'Request withdrawn successfully.'})

@login_required
@require_POST
def assign_job_to_worker(request, job_id, worker_id):
    """Job Provider assigns a specific job to a worker who accepted the invitation."""
    job = get_object_or_404(ServiceJob, id=job_id, provider=request.user)
    from django.contrib.auth import get_user_model
    User = get_user_model()
    worker = get_object_or_404(User, id=worker_id)
    
    if job.worker:
        return JsonResponse({'error': 'This job is already assigned.'}, status=400)
        
    # Check if worker accepted a request from this provider
    # Either a generic request or one specifically for this job
    if not ServiceRequest.objects.filter(provider=request.user, worker=worker, status='accepted').exists():
        return JsonResponse({'error': 'Worker must accept your invitation first.'}, status=403)
        
    job.worker = worker
    job.status = 'Accepted'
    job.save()
    
    # Update service request status to 'assigned' for the relevant request
    ServiceRequest.objects.filter(provider=request.user, worker=worker, status='accepted').update(status='assigned')
    
    Notification.objects.create(
        user=worker,
        actor=f"{request.user.first_name or request.user.username} {request.user.last_name}".strip(),
        verb='assigned you to the job:',
        target=job.title,
        redirect_url='/services/worker/'
    )
    
    return JsonResponse({'status': 'ok', 'message': f'Job assigned to {worker.first_name or worker.username}'})

@login_required
def provider_dashboard(request):
    if hasattr(request.user, 'profile') and request.user.profile.role == 'Worker':
        return redirect('worker_dashboard')
    
    # Active requests for Provider
    active_jobs = ServiceJob.objects.filter(provider=request.user).exclude(status__in=['Completed', 'Cancelled']).order_by('-created_at')
    completed_jobs = ServiceJob.objects.filter(provider=request.user, status='Completed').order_by('-updated_at')
    total_jobs_posted = ServiceJob.objects.filter(provider=request.user).count()
    
    # Service requests sent by this provider
    service_requests = ServiceRequest.objects.filter(provider=request.user).select_related('worker', 'worker__profile').order_by('-timestamp')
    accepted_workers = [req.worker for req in service_requests if req.status == 'accepted']
    
    # Job applications for this provider's jobs
    job_applications = JobApplication.objects.filter(job__provider=request.user, status='pending').select_related('worker', 'job', 'worker__profile')
    
    context = {
        'active_jobs': active_jobs,
        'completed_jobs': completed_jobs,
        'total_jobs_posted': total_jobs_posted,
        'service_requests': service_requests,
        'accepted_workers': accepted_workers,
        'job_applications': job_applications,
    }
    return render(request, 'dashboard_provider.html', context)

@login_required
def dashboard_redirect(request):
    if hasattr(request.user, 'profile') and request.user.profile.role == 'Worker':
        return redirect('worker_dashboard')
    else:
        return redirect('provider_dashboard')

@login_required
def worker_dashboard(request):
    if hasattr(request.user, 'profile') and request.user.profile.role == 'Job Provider':
        return redirect('provider_dashboard')
        
    # Jobs assigned to this worker
    assigned_jobs = ServiceJob.objects.filter(worker=request.user).exclude(status__in=['Completed', 'Cancelled']).order_by('-created_at')
    
    # Completed jobs by this worker
    completed_jobs = ServiceJob.objects.filter(worker=request.user, status='Completed').order_by('-updated_at')
    
    # Nearby pending jobs (simple fetch for now)
    available_jobs = ServiceJob.objects.filter(status='Pending', worker__isnull=True).order_by('-created_at')
    
    # Service requests received by this worker
    service_requests = ServiceRequest.objects.filter(worker=request.user).select_related('provider').order_by('-timestamp')
    
    context = {
        'assigned_jobs': assigned_jobs,
        'completed_jobs': completed_jobs,
        'available_jobs': available_jobs,
        'service_requests': service_requests,
    }
    return render(request, 'dashboard_worker.html', context)

@login_required
def post_job_page(request):
    """Dedicated page for posting a new job with a form."""
    if hasattr(request.user, 'profile') and request.user.profile.role == 'Worker':
        from django.contrib import messages
        messages.error(request, 'Workers cannot post jobs. Switch to a Job Provider account.')
        return redirect('worker_dashboard')
        
    if request.method == 'POST':
        from social.models import Notification
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        price = request.POST.get('price', '').strip()
        category = request.POST.get('job_category', 'Other').strip()
        other_category_name = request.POST.get('other_category_name', '').strip()
        address = request.POST.get('address', '').strip()
        lat = request.POST.get('lat', '0').strip()
        lon = request.POST.get('lon', '0').strip()
        scheduled_time = request.POST.get('scheduled_time', '').strip()

        if category == 'Other' and other_category_name:
            category = other_category_name
        
        errors = []
        if not title:
            errors.append('Job title is required.')
        if not description:
            errors.append('Job description is required.')
        
        if errors:
            from django.contrib import messages
            for err in errors:
                messages.error(request, err)
            return render(request, 'post_job.html', {
                'form_data': request.POST
            })
        
        # Handle optional scheduled_time
        from django.utils.dateparse import parse_datetime
        sched_dt = parse_datetime(scheduled_time) if scheduled_time else None

        job = ServiceJob.objects.create(
            provider=request.user,
            title=title,
            category=category,
            description=description,
            address=address,
            price=float(price) if price else None,
            lat=float(lat) if lat else 0,
            lon=float(lon) if lon else 0,
            scheduled_time=sched_dt
        )
        
        Notification.objects.create(
            user=request.user,
            actor='System',
            verb='Job request created successfully:',
            target=job.title
        )
        
        from django.contrib import messages
        messages.success(request, f'Job "{job.title}" posted successfully!')
        return redirect('provider_dashboard')
    
    return render(request, 'post_job.html')

@login_required
def find_jobs(request):
    """Page for workers to search and filter available jobs."""
    if hasattr(request.user, 'profile') and request.user.profile.role == 'Job Provider':
        from django.contrib import messages
        messages.info(request, 'Job Providers should use the Find Workers page.')
        return redirect('jobs')
        
    filter_skill = request.GET.get('filter', '').strip()
    
    # Base query for all pending jobs not yet assigned
    available_jobs = ServiceJob.objects.filter(status='Pending', worker__isnull=True).order_by('-created_at')
    
    # Skill filtering based on the 'filter' param
    if filter_skill:
        from django.db.models import Q
        available_jobs = available_jobs.filter(
            Q(title__icontains=filter_skill) |
            Q(description__icontains=filter_skill)
        )
        
    context = {
        'service_jobs': available_jobs,
        'current_filter': filter_skill
    }
    return render(request, 'jobs.html', context)
    
@login_required
@require_POST
def post_job(request):
    # API for provider to post a job
    if request.user.profile.role == 'Worker':
        return JsonResponse({'error': 'Workers cannot post jobs'}, status=403)
        
    data = json.loads(request.body)
    job = ServiceJob.objects.create(
        provider=request.user,
        title=data.get('title'),
        description=data.get('description', ''),
        lat=float(data.get('lat', 0)),
        lon=float(data.get('lon', 0))
    )
    
    Notification.objects.create(
        user=request.user,
        actor='System',
        verb='Job request created successfully:',
        target=job.title
    )
    
    return JsonResponse({'status': 'success', 'job_id': job.id})

@login_required
def accept_job(request, job_id):
    """Worker directly accepts a job — assigns them immediately."""
    job = get_object_or_404(ServiceJob, id=job_id)
    
    # Determine where to redirect back to
    referer = request.META.get('HTTP_REFERER', '')
    if 'find' in referer or 'jobs' in referer:
        redirect_to = referer
    else:
        redirect_to = request.META.get('HTTP_REFERER', reverse('find_jobs'))
    
    # Can't accept own job
    if job.provider == request.user:
        messages.warning(request, "You cannot accept your own job.")
        return redirect(redirect_to)
    
    # Check if already assigned to this worker
    if job.worker == request.user:
        messages.info(request, "You have already accepted this job.")
        return redirect(redirect_to)

    from .models import JobApplication

    if job.status == 'Pending' and job.worker is None:
        # Check if already applied
        if JobApplication.objects.filter(job=job, worker=request.user).exists():
            messages.info(request, "You have already applied for this job.")
            return redirect(redirect_to)

        # Create a job application instead of instantly assigning
        JobApplication.objects.create(
            job=job,
            worker=request.user,
            status='pending'
        )
        
        # Notify the job provider
        Notification.objects.create(
            user=job.provider,
            actor=f"{request.user.first_name or request.user.username} {request.user.last_name}".strip(),
            verb='applied for your job:',
            target=job.title,
            redirect_url='/services/provider/'
        )
        
        messages.success(request, f'You applied for "{job.title}"! The provider will review your application.')
        return redirect('worker_dashboard')
    else:
        messages.info(request, "This job is no longer available.")
    return redirect(redirect_to)

@login_required
@require_POST
def respond_job_application(request, application_id):
    """Provider decides to assign or reject a job applicant."""
    application = get_object_or_404(JobApplication, id=application_id, job__provider=request.user)
    action = request.POST.get('action') # 'assign' or 'reject'
    job = application.job

    if action == 'assign':
        # Assign job to this worker
        job.worker = application.worker
        job.status = 'Accepted'
        job.save()
        
        application.status = 'accepted'
        application.save()
        
        # Reject other applications for this job
        JobApplication.objects.filter(job=job, status='pending').exclude(id=application.id).update(status='rejected')
        
        Notification.objects.create(
            user=application.worker,
            actor=f"{request.user.first_name or request.user.username} {request.user.last_name}".strip(),
            verb='assigned you to the job:',
            target=job.title,
            redirect_url='/services/worker/'
        )
        messages.success(request, f"Job assigned to {application.worker.username}.")
        
    elif action == 'reject':
        application.status = 'rejected'
        application.save()
        
        Notification.objects.create(
            user=application.worker,
            actor=f"{request.user.first_name or request.user.username} {request.user.last_name}".strip(),
            verb='declined your application for:',
            target=job.title
        )
        messages.info(request, "Application declined.")
        
    return redirect('provider_dashboard')

@login_required
def update_status(request, job_id):
    job = get_object_or_404(ServiceJob, id=job_id)
    if request.user == job.worker:
        new_status = request.POST.get('status')
        
        # If worker marks as Completed, set to Pending Approval instead
        if new_status == 'Completed':
            new_status = 'Pending Approval'
        
        if new_status in dict(ServiceJob.STATUS_CHOICES).keys():
            job.status = new_status
            job.save()
            
            if new_status == 'Pending Approval':
                Notification.objects.create(
                    user=job.provider,
                    actor=f"{request.user.first_name or request.user.username} {request.user.last_name}".strip(),
                    verb='has marked the job as completed. Please verify and approve:',
                    target=job.title,
                    redirect_url=f'/services/job/{job.id}/detail/'
                )
            else:
                Notification.objects.create(
                    user=job.provider,
                    actor=f"{request.user.first_name or request.user.username} {request.user.last_name}".strip(),
                    verb=f'updated job status to {new_status}:',
                    target=job.title
                )
            
            # If "On the Way", initialize tracking
            if new_status == 'On the Way' and job.lat and job.lon:
                tracking, created = JobTracking.objects.get_or_create(job=job)
                
    return redirect('worker_dashboard')


@login_required
@require_POST
def approve_completion(request, job_id):
    """Provider approves or rejects the worker's completion claim."""
    job = get_object_or_404(ServiceJob, id=job_id)
    
    if request.user != job.provider:
        messages.error(request, "Only the job provider can approve or reject completion.")
        return redirect('job_detail', job_id=job.id)
    
    if job.status != 'Pending Approval':
        messages.info(request, "This job is not pending approval.")
        return redirect('job_detail', job_id=job.id)
    
    action = request.POST.get('action')  # 'approve' or 'reject'
    
    if action == 'approve':
        job.status = 'Completed'
        job.save()
        messages.success(request, f'Job "{job.title}" has been approved as completed!')
        
        Notification.objects.create(
            user=job.worker,
            actor=f"{request.user.first_name or request.user.username} {request.user.last_name}".strip(),
            verb='approved your job completion for:',
            target=job.title,
            redirect_url=f'/services/job/{job.id}/detail/'
        )
    elif action == 'reject':
        job.status = 'Arrived'  # Revert back to Arrived status
        job.save()
        messages.info(request, f'Completion for "{job.title}" has been rejected. The worker has been notified.')
        
        Notification.objects.create(
            user=job.worker,
            actor=f"{request.user.first_name or request.user.username} {request.user.last_name}".strip(),
            verb='rejected your completion claim. Please revisit the work for:',
            target=job.title,
            redirect_url=f'/services/job/{job.id}/detail/'
        )
    
    return redirect('job_detail', job_id=job.id)

@login_required
@require_POST
def update_location(request, job_id):
    # Worker pushes their GPS location
    job = get_object_or_404(ServiceJob, id=job_id)
    if job.worker != request.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    if job.status != 'On the Way':
        return JsonResponse({'error': 'Job not active'}, status=400)
    
    data = json.loads(request.body)
    lat = float(data.get('lat'))
    lon = float(data.get('lon'))
    
    tracking, created = JobTracking.objects.get_or_create(job=job)
    tracking.current_lat = lat
    tracking.current_lon = lon
    
    # Calculate ETA using Haversine
    from .utils import haversine, calculate_eta
    if job.lat and job.lon:
        distance = haversine(lat, lon, job.lat, job.lon)
        eta = calculate_eta(distance)
        tracking.eta_minutes = eta
        
    tracking.save()
    return JsonResponse({'status': 'success', 'eta': tracking.eta_minutes})

@login_required
def get_location(request, job_id):
    # Provider polls for worker location
    job = get_object_or_404(ServiceJob, id=job_id)
    if job.provider != request.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    try:
        tracking = job.tracking
        if tracking.current_lat is None or tracking.current_lon is None:
            return JsonResponse({'error': 'No location data yet'}, status=404)
            
        return JsonResponse({
            'lat': tracking.current_lat,
            'lon': tracking.current_lon,
            'eta': tracking.eta_minutes,
            'delay_reason': tracking.delay_reason
        })
    except JobTracking.DoesNotExist:
        return JsonResponse({'error': 'Tracking not found'}, status=404)

@login_required
def nearby_map(request):
    import json
    from accounts.models import Profile
    from services.models import ServiceJob
    
    # Get user role
    user_role = request.user.profile.role if hasattr(request.user, 'profile') else 'User'

    # Fetch workers
    workers_qs = Profile.objects.filter(role__in=['Worker', 'Both'], latitude__isnull=False, longitude__isnull=False).select_related('user')
    workers_data = []
    for w in workers_qs:
        workers_data.append({
            'id': w.user.id,
            'name': w.full_name or (f"{w.user.first_name or w.user.username} {w.user.last_name}").strip(),
            'skill': w.primary_category or 'General Handyman',
            'lat': w.latitude,
            'lon': w.longitude,
            'rating': w.rating or 0.0,
            'status': 'Available' if w.is_available else 'Busy'
        })
        
    # Fetch pending jobs
    jobs_qs = ServiceJob.objects.filter(status='Pending', lat__isnull=False, lon__isnull=False).select_related('provider')
    jobs_data = []
    for j in jobs_qs:
        jobs_data.append({
            'id': j.id,
            'title': j.title,
            'category': j.title, # Assuming title represents the kind of work roughly
            'lat': j.lat,
            'lon': j.lon,
            'price': float(j.price) if j.price else 0.0,
            'provider_id': j.provider.id,
            'provider_name': (f"{j.provider.first_name or j.provider.username} {j.provider.last_name}").strip(),
            'description': j.description or 'No extra details provided.',
            'address': j.address or 'Location not specified',
            'created_at': j.created_at.strftime("%b %d, %Y") if j.created_at else '',
            'scheduled_time': j.scheduled_time.strftime("%b %d, %Y %I:%M %p") if j.scheduled_time else 'ASAP',
            'status': j.status
        })

    context = {
        'workers_json': json.dumps(workers_data),
        'jobs_json': json.dumps(jobs_data),
        'user_role': user_role
    }
    return render(request, 'nearby_map.html', context)
@login_required
def job_tracking(request, job_id):
    """Real-time job tracking page with Google Maps route display and ETA."""
    job = get_object_or_404(ServiceJob, id=job_id)
    
    # Only provider or assigned worker can view tracking
    if request.user != job.provider and request.user != job.worker:
        return redirect('home')
    
    is_worker = (request.user == job.worker)
    
    context = {
        'job': job,
        'is_worker': is_worker,
        'job_lat': job.lat,
        'job_lon': job.lon,
    }
    return render(request, 'job_tracking.html', context)

@login_required
def job_detail(request, job_id):
    """Detailed view for a specific job, tracking activity and applications."""
    job = get_object_or_404(ServiceJob, id=job_id)
    
    # Check permissions (Provider, Worker, or Applicant)
    is_related = request.user == job.provider or request.user == job.worker
    has_applied = JobApplication.objects.filter(job=job, worker=request.user).exists()
    
    if not (is_related or has_applied or request.user.is_superuser):
        messages.error(request, "You do not have permission to view this job.")
        return redirect('home')

    applications = JobApplication.objects.filter(job=job).select_related('worker', 'worker__profile').order_by('-timestamp')
    reviews = Review.objects.filter(job=job).select_related('reviewer', 'reviewee')
    user_has_reviewed = reviews.filter(reviewer=request.user).exists()
    
    context = {
        'job': job,
        'applications': applications,
        'reviews': reviews,
        'user_has_reviewed': user_has_reviewed,
        'is_provider': request.user == job.provider,
        'is_worker': request.user == job.worker,
    }
    return render(request, 'job_detail.html', context)

@login_required
@require_POST
def submit_review(request, job_id):
    """Submit a review for a completed job."""
    job = get_object_or_404(ServiceJob, id=job_id)
    
    if job.status != 'Completed':
        messages.error(request, "You can only review completed jobs.")
        return redirect('job_detail', job_id=job.id)
    
    # Determine reviewer and reviewee
    if request.user == job.provider:
        reviewee = job.worker
    elif request.user == job.worker:
        reviewee = job.provider
    else:
        messages.error(request, "You are not authorized to review this job.")
        return redirect('job_detail', job_id=job.id)
    
    if not reviewee:
        messages.error(request, "Cannot submit a review — no counterparty found.")
        return redirect('job_detail', job_id=job.id)
    
    # Check if already reviewed
    if Review.objects.filter(job=job, reviewer=request.user).exists():
        messages.info(request, "You have already submitted a review for this job.")
        return redirect('job_detail', job_id=job.id)
    
    try:
        rating = int(request.POST.get('rating', 3))
        professionalism = int(request.POST.get('professionalism', 3))
        communication = int(request.POST.get('communication', 3))
        timeliness = int(request.POST.get('timeliness', 3))
    except (ValueError, TypeError):
        rating = professionalism = communication = timeliness = 3
    
    comment = request.POST.get('comment', '').strip()
    would_recommend = request.POST.get('would_recommend') == 'on'
    
    Review.objects.create(
        job=job,
        reviewer=request.user,
        reviewee=reviewee,
        rating=min(max(rating, 1), 5),
        professionalism=min(max(professionalism, 1), 5),
        communication=min(max(communication, 1), 5),
        timeliness=min(max(timeliness, 1), 5),
        comment=comment,
        would_recommend=would_recommend
    )
    
    messages.success(request, "Your review has been submitted. Thank you!")
    return redirect('job_detail', job_id=job.id)

