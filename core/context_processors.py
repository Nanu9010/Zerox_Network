from core.models import Notification


def notification_count(request):
    """Add unread notification count to all templates"""
    if request.user.is_authenticated:
        return {'unread_notifications': request.user.notifications.filter(is_read=False).count()}
    return {'unread_notifications': 0}
