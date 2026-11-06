from rest_framework.permissions import AllowAny

from base.views import FilteredReadOnlyViewSet, LangFilteredViewSet
from .models import Game, GameCategory, GameSound, LobbyPageLabel
from .serializers import GameCategorySerializer, GameSerializer, GameSoundSerializer, LobbyPageLabelSerializer


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


class GameSoundViewSet(FilteredReadOnlyViewSet):
    """Only sounds that can really be played: active, with an uploaded file."""

    queryset = GameSound.objects.filter(is_active=True).exclude(file="")
    serializer_class = GameSoundSerializer
    permission_classes = [AllowAny]
