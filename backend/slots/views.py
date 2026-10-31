from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from base.views import FilteredReadOnlyViewSet, LangFilteredViewSet
from errors.exceptions import CodedError
from wallet import services as wallet_services
from wallet.services import InsufficientFunds
from . import services
from .models import SlotSound, SlotSpin, SlotSymbol, SlotSymbolName, ZeusPageLabel
from .serializers import (
    SlotSoundSerializer,
    SlotSpinListSerializer,
    SlotSpinRequestSerializer,
    SlotSpinSerializer,
    SlotSymbolNameSerializer,
    SlotSymbolSerializer,
    ZeusPageLabelSerializer,
)


class SlotSpinViewSet(FilteredReadOnlyViewSet):
    """GET lists the player's last 50 spins. POST {game, amount, bonus_buy} plays one round."""

    queryset = SlotSpin.objects.select_related("game")
    list_limit = 50

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_serializer_class(self):
        return SlotSpinListSerializer if self.action == "list" else SlotSpinSerializer

    def list(self, request, *args, **kwargs):
        rows = self.filter_queryset(self.get_queryset()).defer("result")[: self.list_limit]
        return Response(self.get_serializer(rows, many=True).data)

    def create(self, request, *args, **kwargs):
        serializer = SlotSpinRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            spin = services.play_spin(request.user, data["game"], data["amount"], data["bonus_buy"])
        except InsufficientFunds as exc:
            raise CodedError("not_enough_lc", "Not enough LC.") from exc
        except services.SlotError as exc:
            raise CodedError(exc.code, str(exc), **exc.params) from exc

        wallet = wallet_services.open_wallet(request.user)
        body = {
            **self.get_serializer(spin).data,
            "balance": str(wallet.balance),
            "jackpot_pools": {tier: str(amount) for tier, amount in wallet_services.jackpot_pools().items()},
        }
        return Response(body, status=status.HTTP_201_CREATED)


class SlotSymbolViewSet(FilteredReadOnlyViewSet):
    queryset = SlotSymbol.objects.all()
    serializer_class = SlotSymbolSerializer
    permission_classes = [AllowAny]


class SlotSymbolNameViewSet(LangFilteredViewSet):
    queryset = SlotSymbolName.objects.all()
    serializer_class = SlotSymbolNameSerializer


class SlotSoundViewSet(FilteredReadOnlyViewSet):
    """Only sounds that can really be played: active, with an uploaded file."""

    queryset = SlotSound.objects.filter(is_active=True).exclude(file="")
    serializer_class = SlotSoundSerializer
    permission_classes = [AllowAny]


class ZeusPageLabelViewSet(LangFilteredViewSet):
    queryset = ZeusPageLabel.objects.all()
    serializer_class = ZeusPageLabelSerializer
