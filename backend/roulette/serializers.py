from rest_framework import serializers

from base.serializers import ModelSerializer
from . import engine, feed
from .models import RouletteLine, RoulettePageLabel, RouletteRound, RouletteSlip


class BetRequestSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=36)
    # Each line is checked by services.place_bet, so that a bad one has the code invalid_bet.
    lines = serializers.ListField(child=serializers.DictField(), allow_empty=False)


class RouletteLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = RouletteLine
        fields = ["bet_type", "value", "multiplier", "amount", "payout"]


class RouletteSlipSerializer(serializers.ModelSerializer):
    round = serializers.IntegerField(source="round.number")
    seat = serializers.SerializerMethodField()
    lines = RouletteLineSerializer(many=True)

    class Meta:
        model = RouletteSlip
        fields = ["id", "round", "seat", "amount", "payout", "lines", "created_at"]

    def get_seat(self, slip):
        return feed.slip_seat(slip.user_id)


class RouletteRoundSerializer(serializers.ModelSerializer):
    """Only for settled rounds: this is where the seed is public."""

    color = serializers.SerializerMethodField()
    commitment = serializers.CharField(source="chain.commitment")

    class Meta:
        model = RouletteRound
        fields = [
            "number",
            "result",
            "color",
            "seed",
            "seed_hash",
            "position",
            "commitment",
            "spin_started_at",
            "settled_at",
        ]

    def get_color(self, current):
        return engine.color(current.result)


class RoulettePageLabelSerializer(ModelSerializer):
    class Meta:
        model = RoulettePageLabel
        fields = "__all__"
