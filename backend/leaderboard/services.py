from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone

from wallet.models import Transaction

GAME_KINDS = [Transaction.Kind.BET, Transaction.Kind.WIN, Transaction.Kind.JACKPOT]


def weekly_top(limit=20, now=None):
    """Top players by net game result over the last 7 days. Bonuses and signup do not count."""
    since = (now or timezone.now()) - timedelta(days=7)
    rows = (
        Transaction.objects.filter(kind__in=GAME_KINDS, created_at__gte=since)
        .values("wallet__user__id", "wallet__user__display_name", "wallet__user__email")
        .annotate(net=Sum("amount"), bets=Count("id", filter=Q(kind=Transaction.Kind.BET)))
        .order_by("-net", "wallet__user__id")[:limit]
    )
    return [
        {
            "rank": i + 1,
            "player": row["wallet__user__display_name"] or row["wallet__user__email"].split("@")[0],
            "net": row["net"],
            "bets": row["bets"],
        }
        for i, row in enumerate(rows)
    ]
