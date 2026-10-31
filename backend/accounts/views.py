from django.conf import settings
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainSerializer, TokenRefreshSerializer

from base.views import SingleObjectViewSet
from .authentication import CookieJWTAuthentication, enforce_csrf
from .cookies import clear_auth_cookies, set_access_cookie, set_auth_cookies
from .models import User
from .serializers import MeSerializer, RegisterSerializer


def logged_in_response(request, user, status_code):
    response = Response(MeSerializer(user).data, status=status_code)
    set_auth_cookies(request, response, user)
    return response


class RegisterViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """POST creates a player, opens a wallet with the signup grant and logs the player in."""

    serializer_class = RegisterSerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return logged_in_response(request, serializer.save(), status.HTTP_201_CREATED)


class TokenViewSet(viewsets.GenericViewSet):
    """POST logs in with email and password. The tokens stay in httpOnly cookies."""

    serializer_class = TokenObtainSerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    def get_authenticate_header(self, request):
        # Without this header DRF turns the 401 of a wrong password into a 403.
        return CookieJWTAuthentication().authenticate_header(request)

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return logged_in_response(request, serializer.user, status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def refresh(self, request):
        """Works with an expired access cookie, so CSRF is checked here and not by the auth class."""
        enforce_csrf(request)
        serializer = TokenRefreshSerializer(data={"refresh": request.COOKIES.get(settings.AUTH_REFRESH_COOKIE, "")})
        try:
            serializer.is_valid(raise_exception=True)
        except (TokenError, ValidationError, AuthenticationFailed, User.DoesNotExist):
            response = Response({"detail": "Session expired. Log in again."}, status=status.HTTP_401_UNAUTHORIZED)
            clear_auth_cookies(response)
            return response

        response = Response(status=status.HTTP_204_NO_CONTENT)
        set_access_cookie(response, serializer.validated_data["access"])
        return response


class LogoutViewSet(viewsets.ViewSet):
    """POST deletes the JWT cookies. Works with an expired access cookie too."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def create(self, request):
        enforce_csrf(request)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_auth_cookies(response)
        return response


class MeViewSet(SingleObjectViewSet):
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user
