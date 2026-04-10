"""
Authentication backend: login by phone number or email.
"""
from django.contrib.auth.backends import ModelBackend
from .models import User


class PhoneOrEmailBackend(ModelBackend):
    """Allow login with phone number OR email."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        # Try email first
        user = None
        if '@' in username:
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                pass
        else:
            # Try phone (normalize: strip spaces/dashes)
            phone = username.replace(' ', '').replace('-', '')
            try:
                user = User.objects.get(phone=phone)
            except User.DoesNotExist:
                # Try with +
                if not phone.startswith('+'):
                    try:
                        user = User.objects.get(phone='+' + phone)
                    except User.DoesNotExist:
                        pass

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
