"""
Context processor: inject portal_unread_count for authenticated admin users.
"""


def portal_unread(request):
    if request.user.is_authenticated:
        from .models import PortalNotification
        count = PortalNotification.objects.filter(user=request.user, is_read=False).count()
        return {'portal_unread_count': count}
    return {'portal_unread_count': 0}
