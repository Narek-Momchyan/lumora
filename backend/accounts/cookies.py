from django.conf import settings
from django.middleware.csrf import rotate_token
from rest_framework_simplejwt.tokens import RefreshToken


def _set_cookie(response, name, token, lifetime):
    response.set_cookie(
        name,
        str(token),
        max_age=int(lifetime.total_seconds()),
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )


def set_access_cookie(response, access):
    _set_cookie(response, settings.AUTH_ACCESS_COOKIE, access, settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"])


def set_auth_cookies(request, response, user):
    """Logs the player in: both JWT cookies, plus a new CSRF cookie (set by CsrfViewMiddleware)."""
    refresh = RefreshToken.for_user(user)
    set_access_cookie(response, refresh.access_token)
    _set_cookie(response, settings.AUTH_REFRESH_COOKIE, refresh, settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"])
    rotate_token(request)


def clear_auth_cookies(response):
    for name in [settings.AUTH_ACCESS_COOKIE, settings.AUTH_REFRESH_COOKIE]:
        response.delete_cookie(name, samesite=settings.AUTH_COOKIE_SAMESITE)
