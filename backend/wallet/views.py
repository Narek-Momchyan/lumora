from rest_framework import status, viewsets
from rest_framework.response import Response

from base.views import FilteredReadOnlyViewSet, SingleObjectViewSet
from . import services
from .models import Transaction
from .serializers import TransactionSerializer, WalletSerializer


class WalletViewSet(SingleObjectViewSet):
    serializer_class = WalletSerializer

    def get_object(self):
        return services.open_wallet(self.request.user)


class TransactionViewSet(FilteredReadOnlyViewSet):
    """The player's own ledger, newest first. The list returns the last 100 rows."""

    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    filter_fields = ["kind", "game"]
    list_limit = 100

    def get_queryset(self):
        return super().get_queryset().filter(wallet__user=self.request.user)


class BonusViewSet(viewsets.GenericViewSet):
    """POST claims the daily bonus. 409 with available_at if it was claimed less than 24 h ago."""

    serializer_class = TransactionSerializer

    def create(self, request, *args, **kwargs):
        wallet = services.open_wallet(request.user)
        try:
            tx = services.claim_daily_bonus(wallet)
        except services.BonusNotReady as exc:
            return Response(
                {"detail": "Daily bonus already claimed.", "available_at": exc.available_at},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(self.get_serializer(tx).data, status=status.HTTP_201_CREATED)
