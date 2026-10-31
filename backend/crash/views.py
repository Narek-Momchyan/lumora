from rest_framework import status
from rest_framework.response import Response

from base.views import FilteredReadOnlyViewSet
from errors.exceptions import CodedError
from wallet.services import InsufficientFunds
from . import services
from .models import CrashBet
from .serializers import CrashBetSerializer


class CrashBetViewSet(FilteredReadOnlyViewSet):
    """GET lists the player's last 50 rounds. POST {amount, target} plays one round."""

    queryset = CrashBet.objects.all()
    serializer_class = CrashBetSerializer
    list_limit = 50

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            bet = services.play(request.user, serializer.validated_data["amount"], serializer.validated_data["target"])
        except InsufficientFunds as exc:
            raise CodedError("not_enough_lc", "Not enough LC.") from exc
        except services.CrashError as exc:
            raise CodedError(exc.code, str(exc), **exc.params) from exc
        return Response(self.get_serializer(bet).data, status=status.HTTP_201_CREATED)
