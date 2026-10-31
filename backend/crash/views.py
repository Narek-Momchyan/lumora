from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from base.views import FilteredReadOnlyViewSet, LangFilteredViewSet
from errors.exceptions import CodedError
from wallet.models import Wallet
from wallet.services import InsufficientFunds
from . import services
from .models import CrashPageLabel, CrashRound, RoundBet
from .serializers import BetRequestSerializer, CrashPageLabelSerializer, CrashRoundSerializer, RoundBetSerializer


class CrashBetViewSet(FilteredReadOnlyViewSet):
    """GET lists the player's last 50 bets. POST {amount, target?} bets on the open round."""

    queryset = RoundBet.objects.select_related("round")
    serializer_class = RoundBetSerializer
    list_limit = 50

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = BetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            bet = services.place_bet(
                request.user, serializer.validated_data["amount"], serializer.validated_data.get("target")
            )
        except InsufficientFunds as exc:
            raise CodedError("not_enough_lc", "Not enough LC.") from exc
        except services.CrashError as exc:
            raise CodedError(exc.code, str(exc), status_code=exc.status_code, **exc.params) from exc
        return Response(self._with_balance(bet), status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def cash_out(self, request):
        try:
            bet = services.cash_out(request.user)
        except services.CrashError as exc:
            raise CodedError(exc.code, str(exc), status_code=exc.status_code, **exc.params) from exc
        return Response(self._with_balance(bet))

    def _with_balance(self, bet):
        balance = Wallet.objects.values_list("balance", flat=True).get(user=bet.user)
        return {**self.get_serializer(bet).data, "balance": str(balance)}


class CrashRoundViewSet(FilteredReadOnlyViewSet):
    """The last 50 crashed rounds with their seeds, so that anyone can verify them."""

    queryset = CrashRound.objects.filter(status=CrashRound.Status.CRASHED).select_related("chain")
    serializer_class = CrashRoundSerializer
    permission_classes = [AllowAny]
    list_limit = 50
    lookup_field = "number"
    lookup_value_regex = "[0-9]+"


class CrashPageLabelViewSet(LangFilteredViewSet):
    queryset = CrashPageLabel.objects.all()
    serializer_class = CrashPageLabelSerializer
