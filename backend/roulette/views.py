from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from base.views import FilteredReadOnlyViewSet, LangFilteredViewSet
from errors.exceptions import CodedError
from wallet.models import Wallet
from wallet.services import InsufficientFunds
from . import services
from .models import RoulettePageLabel, RouletteRound, RouletteSlip
from .serializers import (
    BetRequestSerializer,
    RouletteLineSerializer,
    RoulettePageLabelSerializer,
    RouletteRoundSerializer,
    RouletteSlipSerializer,
)


class RouletteBetViewSet(FilteredReadOnlyViewSet):
    """GET lists the player's last 50 slips. POST {key, lines} puts a slip on the open round."""

    queryset = RouletteSlip.objects.select_related("round").prefetch_related("lines")
    serializer_class = RouletteSlipSerializer
    list_limit = 50

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = BetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            slip, created = services.place_bet(
                request.user, serializer.validated_data["key"], serializer.validated_data["lines"]
            )
        except InsufficientFunds as exc:
            raise CodedError("not_enough_lc", "Not enough LC.") from exc
        except services.RouletteError as exc:
            raise CodedError(exc.code, str(exc), status_code=exc.status_code, **exc.params) from exc
        balance = Wallet.objects.values_list("balance", flat=True).get(user=request.user)
        return Response(
            {**self.get_serializer(slip).data, "balance": str(balance)},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=False)
    def last_round(self, request):
        current, lines = services.last_round_lines(request.user)
        return Response(
            {"round": current.number if current else None, "lines": RouletteLineSerializer(lines, many=True).data}
        )


class RouletteRoundViewSet(FilteredReadOnlyViewSet):
    """The last 50 settled rounds with their seeds, so that anyone can verify them."""

    queryset = RouletteRound.objects.filter(status=RouletteRound.Status.SETTLED).select_related("chain")
    serializer_class = RouletteRoundSerializer
    permission_classes = [AllowAny]
    list_limit = 50
    lookup_field = "number"
    lookup_value_regex = "[0-9]+"


class RoulettePageLabelViewSet(LangFilteredViewSet):
    queryset = RoulettePageLabel.objects.all()
    serializer_class = RoulettePageLabelSerializer
