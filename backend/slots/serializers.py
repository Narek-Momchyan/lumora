from rest_framework import serializers

from base.serializers import ModelSerializer
from .models import SlotSound, SlotSpin, SlotSymbol, SlotSymbolName, ZeusPageLabel


class SlotSpinRequestSerializer(serializers.Serializer):
    game = serializers.CharField(max_length=50)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    bonus_buy = serializers.BooleanField(default=False)


class SlotSpinListSerializer(serializers.ModelSerializer):
    """The history: `result` can be large, so it comes only with one spin."""

    game = serializers.SlugRelatedField(slug_field="slug", read_only=True)

    class Meta:
        model = SlotSpin
        fields = [
            "id",
            "game",
            "amount",
            "cost",
            "bonus_buy",
            "payout",
            "free_spins_played",
            "jackpot_tier",
            "jackpot_win",
            "server_seed_hash",
            "client_seed",
            "nonce",
            "created_at",
        ]


class SlotSpinSerializer(SlotSpinListSerializer):
    class Meta(SlotSpinListSerializer.Meta):
        fields = [*SlotSpinListSerializer.Meta.fields, "result"]


class SlotSymbolSerializer(ModelSerializer):
    class Meta:
        model = SlotSymbol
        fields = "__all__"


class SlotSymbolNameSerializer(ModelSerializer):
    class Meta:
        model = SlotSymbolName
        fields = "__all__"


class SlotSoundSerializer(ModelSerializer):
    class Meta:
        model = SlotSound
        fields = ["code", "file"]


class ZeusPageLabelSerializer(ModelSerializer):
    class Meta:
        model = ZeusPageLabel
        fields = "__all__"
