from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone

from base import names
from wallet.models import Transaction

# A refund gives a void bet's stake back, so it counts too: the void bet nets to zero.
GAME_KINDS = [Transaction.Kind.BET, Transaction.Kind.WIN, Transaction.Kind.JACKPOT, Transaction.Kind.REFUND]


def weekly_top(limit=20, now=None):
    """Top players by net game result over the last 7 days. Bonuses and signup do not count."""
    since = (now or timezone.now()) - timedelta(days=7)
    rows = (
        Transaction.objects.filter(kind__in=GAME_KINDS, created_at__gte=since)
        .values("wallet__user__id", "wallet__user__display_name")
        .annotate(net=Sum("amount"), bets=Count("id", filter=Q(kind=Transaction.Kind.BET)))
        .order_by("-net", "wallet__user__id")[:limit]
    )
    return [
        {
            "rank": i + 1,
            "player": names.public_name(row["wallet__user__display_name"], row["wallet__user__id"]),
            "net": row["net"],
            "bets": row["bets"],
        }
        for i, row in enumerate(rows)
    ]
