from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from base.views import FilteredReadOnlyViewSet, SingleObjectViewSet
from .models import Language, Logo
from .serializers import LanguageSerializer, LogoSerializer


class LogoViewSet(SingleObjectViewSet):
    """GET returns the logo as one object, or {} before one is added."""

    queryset = Logo.objects.all()
    serializer_class = LogoSerializer
    permission_classes = [AllowAny]

    def list(self, request, *args, **kwargs):
        logo = self.get_queryset().first()
        return Response(self.get_serializer(logo).data if logo else {})


class LanguageViewSet(FilteredReadOnlyViewSet):
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer
    permission_classes = [AllowAny]
