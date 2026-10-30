from rest_framework import serializers


class LeaderboardRowSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    player = serializers.CharField()
    net = serializers.DecimalField(max_digits=14, decimal_places=2)
    bets = serializers.IntegerField()
