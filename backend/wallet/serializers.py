from rest_framework import serializers

from base.constants import DAILY_BONUS_COOLDOWN
from .models import Transaction, Wallet


class WalletSerializer(serializers.ModelSerializer):
    bonus_available_at = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = ["balance", "last_bonus_at", "bonus_available_at", "updated_at"]

    def get_bonus_available_at(self, obj):
        # null = never claimed. A time in the past = can be claimed now.
        if obj.last_bonus_at is None:
            return None
        return serializers.DateTimeField().to_representation(obj.last_bonus_at + DAILY_BONUS_COOLDOWN)


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ["id", "kind", "amount", "balance_after", "game", "round_id", "created_at"]
