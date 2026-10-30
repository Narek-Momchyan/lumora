from rest_framework.permissions import AllowAny

from base.views import FilteredReadOnlyViewSet
from .models import Game
from .serializers import GameSerializer


class GameViewSet(FilteredReadOnlyViewSet):
    queryset = Game.objects.filter(is_active=True)
    serializer_class = GameSerializer
    permission_classes = [AllowAny]
    filter_fields = ["slug", "category"]
