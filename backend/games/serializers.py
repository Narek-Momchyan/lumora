from rest_framework import serializers

from .models import Game


class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = ["id", "slug", "title", "category", "rtp", "min_bet", "max_bet", "is_featured"]
