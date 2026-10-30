from rest_framework import serializers

from .models import CrashBet


class CrashBetSerializer(serializers.ModelSerializer):
    won = serializers.BooleanField(read_only=True)

    class Meta:
        model = CrashBet
        fields = [
            "id",
            "amount",
            "target",
            "crash_point",
            "payout",
            "won",
            "server_seed_hash",
            "client_seed",
            "nonce",
            "created_at",
        ]
        read_only_fields = ["crash_point", "payout", "server_seed_hash", "client_seed", "nonce", "created_at"]
