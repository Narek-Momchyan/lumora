from rest_framework import serializers

from base.serializers import ModelSerializer
from .models import CrashPageLabel, CrashRound, RoundBet


class BetRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    target = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)


class RoundBetSerializer(serializers.ModelSerializer):
    round = serializers.IntegerField(source="round.number")

    class Meta:
        model = RoundBet
        fields = ["id", "round", "amount", "target", "status", "multiplier", "payout", "created_at"]


class CrashRoundSerializer(serializers.ModelSerializer):
    """Only for crashed rounds: this is where the seed is public."""

    commitment = serializers.CharField(source="chain.commitment")

    class Meta:
        model = CrashRound
        fields = ["number", "crash_point", "seed", "seed_hash", "position", "commitment", "started_at", "crashed_at"]


class CrashPageLabelSerializer(ModelSerializer):
    class Meta:
        model = CrashPageLabel
        fields = "__all__"
