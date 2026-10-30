from rest_framework import status
from rest_framework.response import Response

from base.views import FilteredReadOnlyViewSet
from . import services
from .models import SeedPair
from .serializers import RotateSeedsSerializer, SeedPairSerializer


class SeedPairViewSet(FilteredReadOnlyViewSet):
    """GET lists the player's seed pairs, active first. POST rotates them:

    the active server seed is revealed and a new pair starts (optional `client_seed`).
    """

    queryset = SeedPair.objects.all()
    serializer_class = SeedPairSerializer
    list_limit = 50

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_serializer_class(self):
        return RotateSeedsSerializer if self.action == "create" else SeedPairSerializer

    def list(self, request, *args, **kwargs):
        services.active_seed_pair(request.user)  # the first visit creates the pair
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        revealed, active = services.rotate_seeds(request.user, serializer.validated_data.get("client_seed"))
        return Response(
            {"revealed": SeedPairSerializer(revealed).data, "active": SeedPairSerializer(active).data},
            status=status.HTTP_201_CREATED,
        )
