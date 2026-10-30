from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .serializers import LeaderboardRowSerializer
from .services import weekly_top


class LeaderboardViewSet(viewsets.ViewSet):
    """Weekly top 20 by net game result. Public."""

    permission_classes = [AllowAny]

    def list(self, request):
        return Response(LeaderboardRowSerializer(weekly_top(), many=True).data)
