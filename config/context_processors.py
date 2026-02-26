from django.conf import settings


def google_maps_key(request):
    return {
        'GOOGLE_MAPS_API_KEY': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
    }


def navbar_counts(request):
    """Inject real unread notification and message counts into all templates."""
    if not request.user.is_authenticated:
        return {'unread_notification_count': 0, 'unread_messages_count': 0}

    from social.models import Notification
    from messaging.models import Message

    notif_count = Notification.objects.filter(
        user=request.user, is_read=False
    ).count()

    msg_count = Message.objects.filter(
        receiver=request.user, is_read=False
    ).count()

    return {
        'unread_notification_count': notif_count,
        'unread_messages_count': msg_count,
    }
