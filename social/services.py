from .models import Notification


def create_notification(user, triggered_by, type, message):
    if user == triggered_by:
        return  # ignore self-notifications

    Notification.objects.create(
        user=user,
        triggered_by=triggered_by,
        type=type,
        message=message
    )
