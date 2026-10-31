from base.serializers import ModelSerializer
from .models import Game, GameCategory, LobbyPageLabel


class GameSerializer(ModelSerializer):
    class Meta:
        model = Game
        fields = [
            "id",
            "slug",
            "title",
            "category",
            "rtp",
            "min_bet",
            "max_bet",
            "is_featured",
            "is_playable",
            "image",
        ]


class GameCategorySerializer(ModelSerializer):
    class Meta:
        model = GameCategory
        fields = "__all__"


class LobbyPageLabelSerializer(ModelSerializer):
    class Meta:
        model = LobbyPageLabel
        fields = "__all__"
