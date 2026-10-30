from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny

from base.views import SingleObjectViewSet
from .serializers import MeSerializer, RegisterSerializer


class RegisterViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """POST creates a player and opens a wallet with the signup grant."""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class MeViewSet(SingleObjectViewSet):
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user
