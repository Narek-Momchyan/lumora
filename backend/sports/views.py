from base.views import LangFilteredViewSet
from .models import SportsPageLabel
from .serializers import SportsPageLabelSerializer


class SportsPageLabelViewSet(LangFilteredViewSet):
    queryset = SportsPageLabel.objects.all()
    serializer_class = SportsPageLabelSerializer
