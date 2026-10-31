from rest_framework.permissions import AllowAny

from base.views import FilteredReadOnlyViewSet, LangFilteredViewSet
from .models import Game, GameCategory, LobbyPageLabel
from .serializers import GameCategorySerializer, GameSerializer, LobbyPageLabelSerializer


class GameViewSet(FilteredReadOnlyViewSet):
    queryset = Game.objects.filter(is_active=True)
    serializer_class = GameSerializer
    permission_classes = [AllowAny]
    filter_fields = ["slug", "category"]


class GameCategoryViewSet(LangFilteredViewSet):
    queryset = GameCategory.objects.all()
    serializer_class = GameCategorySerializer


class LobbyPageLabelViewSet(LangFilteredViewSet):
    queryset = LobbyPageLabel.objects.all()
    serializer_class = LobbyPageLabelSerializer
