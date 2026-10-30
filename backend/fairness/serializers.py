from rest_framework import serializers

from .models import SeedPair


class SeedPairSerializer(serializers.ModelSerializer):
    server_seed = serializers.SerializerMethodField()

    class Meta:
        model = SeedPair
        fields = [
            "id",
            "server_seed_hash",
            "server_seed",
            "client_seed",
            "nonce",
            "is_active",
            "created_at",
            "revealed_at",
        ]

    def get_server_seed(self, obj):
        # The secret is shown only after the pair was rotated out.
        return None if obj.is_active else obj.server_seed


class RotateSeedsSerializer(serializers.Serializer):
    client_seed = serializers.RegexField(
        r"^[A-Za-z0-9_-]{1,64}$",
        required=False,
        error_messages={"invalid": "Use 1-64 letters, digits, - or _."},
    )
