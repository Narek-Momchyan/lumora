from django.conf import settings
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


def enforce_csrf(request):
    """Same check as the admin session: unsafe methods need a matching X-CSRFToken."""
    try:
        SessionAuthentication().enforce_csrf(request)
    except PermissionDenied as exc:
        raise PermissionDenied(str(exc.detail), code="csrf_failed") from exc


class CookieJWTAuthentication(JWTAuthentication):
    """Reads the access token from its httpOnly cookie.

    A missing, expired or bad cookie means an anonymous request: private endpoints
    answer 401, while public ones keep working for a player with a stale cookie.
    """

    def authenticate(self, request):
        raw_token = request.COOKIES.get(settings.AUTH_ACCESS_COOKIE)
        if not raw_token:
            return None

        try:
            token = self.get_validated_token(raw_token)
            user = self.get_user(token)
        except (InvalidToken, AuthenticationFailed):
            return None

        enforce_csrf(request)
        return user, token
