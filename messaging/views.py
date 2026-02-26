from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.contrib.auth import get_user_model
import json
from .models import Message

User = get_user_model()

@login_required
def inbox_view(request):
    user_id = request.GET.get('user')
    specific_user = None
    if user_id:
        try:
            specific_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            pass

    # Fetch chronological messages involving the user
    messages = Message.objects.filter(Q(sender=request.user) | Q(receiver=request.user)).select_related('sender', 'receiver').order_by('-timestamp')
    
    contacts = []
    seen_users = set()
    
    for msg in messages:
        other_user = msg.receiver if msg.sender == request.user else msg.sender
        if other_user not in seen_users:
            seen_users.add(other_user)
            contacts.append({
                'user': other_user,
                'latest_message': msg,
            })

    # Also include users from accepted/assigned ServiceRequests
    from services.models import ServiceRequest
    service_reqs = ServiceRequest.objects.filter(
        (Q(provider=request.user) | Q(worker=request.user)) & 
        Q(status__in=['accepted', 'assigned'])
    ).select_related('provider', 'worker')

    for req in service_reqs:
        other_user = req.worker if req.provider == request.user else req.provider
        if other_user not in seen_users:
            seen_users.add(other_user)
            contacts.append({
                'user': other_user,
                'latest_message': None,
            })
            
    # If a specific user was requested but not in contacts, add them
    if specific_user and specific_user not in seen_users:
        contacts.insert(0, {
            'user': specific_user,
            'latest_message': None, # No messages yet
        })
        
    active_user_id = specific_user.id if specific_user else None
            
    return render(request, 'inbox.html', {'contacts': contacts, 'active_user_id': active_user_id})

@login_required
def fetch_chat(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    messages = Message.objects.filter(
        (Q(sender=request.user) & Q(receiver=other_user)) | 
        (Q(sender=other_user) & Q(receiver=request.user))
    ).order_by('timestamp')
    
    # Mark messages as read
    Message.objects.filter(sender=other_user, receiver=request.user, is_read=False).update(is_read=True)
    
    chat_data = []
    for msg in messages:
        msg_data = {
            'id': msg.id,
            'is_sender': msg.sender == request.user,
            'content': msg.content,
            'timestamp': msg.timestamp.strftime("%I:%M %p"),
            'date': msg.timestamp.strftime("%b %d, %Y"),
        }
        if msg.attachment:
            msg_data['attachment_url'] = msg.attachment.url
            msg_data['attachment_name'] = msg.attachment.name.split('/')[-1]
            # Check if it's an image
            ext = msg.attachment.name.lower().split('.')[-1] if '.' in msg.attachment.name else ''
            msg_data['is_image'] = ext in ('jpg', 'jpeg', 'png', 'gif', 'webp', 'svg')
        chat_data.append(msg_data)
        
    return JsonResponse({
        'status': 'success',
        'chat': chat_data,
        'other_user': {
            'id': other_user.id,
            'name': (f"{other_user.first_name or other_user.username} {other_user.last_name}").strip(),
            'role': other_user.profile.role if hasattr(other_user, 'profile') else 'User'
        }
    })

@login_required
@require_POST
def send_message(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    
    # Handle both JSON and multipart/form-data
    content_type = request.content_type or ''
    
    if 'multipart/form-data' in content_type:
        # File upload
        content = request.POST.get('content', '').strip()
        attachment = request.FILES.get('attachment')
        
        if not content and not attachment:
            return JsonResponse({'error': 'Message or attachment required'}, status=400)
        
        msg = Message.objects.create(
            sender=request.user,
            receiver=other_user,
            content=content,
            attachment=attachment,
        )
        
        response_data = {
            'status': 'success',
            'message': {
                'id': msg.id,
                'is_sender': True,
                'content': msg.content,
                'timestamp': msg.timestamp.strftime("%I:%M %p"),
            }
        }
        if msg.attachment:
            response_data['message']['attachment_url'] = msg.attachment.url
            response_data['message']['attachment_name'] = msg.attachment.name.split('/')[-1]
            ext = msg.attachment.name.lower().split('.')[-1] if '.' in msg.attachment.name else ''
            response_data['message']['is_image'] = ext in ('jpg', 'jpeg', 'png', 'gif', 'webp', 'svg')
        
        return JsonResponse(response_data)
    else:
        # JSON body
        try:
            data = json.loads(request.body)
            content = data.get('content', '').strip()
            
            if not content:
                return JsonResponse({'error': 'Message content cannot be empty'}, status=400)
                
            msg = Message.objects.create(
                sender=request.user,
                receiver=other_user,
                content=content
            )
            
            return JsonResponse({
                'status': 'success', 
                'message': {
                    'id': msg.id,
                    'is_sender': True,
                    'content': msg.content,
                    'timestamp': msg.timestamp.strftime("%I:%M %p")
                }
            })
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
