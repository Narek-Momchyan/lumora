from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from base.views import FilteredReadOnlyViewSet, LangFilteredViewSet, SingleObjectViewSet
from .models import HeaderLabel, Language, Logo, SidebarItem
from .serializers import HeaderLabelSerializer, LanguageSerializer, LogoSerializer, SidebarItemSerializer


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


class SidebarItemViewSet(LangFilteredViewSet):
    queryset = SidebarItem.objects.all()
    serializer_class = SidebarItemSerializer


class HeaderLabelViewSet(LangFilteredViewSet):
    queryset = HeaderLabel.objects.all()
    serializer_class = HeaderLabelSerializer
