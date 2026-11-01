from decimal import Decimal

from django.conf import settings
from django.db import models

from base.constants import LANG_CHOICES
from fairness.models import HashChain

DEFAULT_BOT_NAMES = "\n".join(
    ["nova_88", "kite", "lumen_x", "echo", "arman.dev", "pixel", "orbit", "zara_7", "vega", "mirage", "nox", "tigran_k"]
)


class CrashChain(HashChain):
    class Meta:
        verbose_name_plural = "Crash chains"
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(fields=["commitment"], name="unique_crash_chain_commitment"),
        ]


class CrashRound(models.Model):
    """One shared round. `seed` and `crash_point` stay secret until the round has crashed."""

    class Status(models.TextChoices):
        BETTING = "betting", "Betting"
        FLYING = "flying", "Flying"
        CRASHED = "crashed", "Crashed"

    number = models.PositiveBigIntegerField()
    chain = models.ForeignKey(CrashChain, related_name="rounds", on_delete=models.PROTECT)
    position = models.PositiveIntegerField(help_text="Place in the chain, the first round is 0")
    seed = models.CharField(max_length=64)
    seed_hash = models.CharField(max_length=64)
    crash_point = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.BETTING)
    betting_ends_at = models.DateTimeField()
    started_at = models.DateTimeField(null=True, blank=True)
    crashed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Crash rounds"
        ordering = ["-number"]
        constraints = [
            models.UniqueConstraint(fields=["number"], name="unique_crash_round_number"),
            models.UniqueConstraint(fields=["chain", "position"], name="unique_crash_round_chain_position"),
        ]
        indexes = [models.Index(fields=["status", "-number"], name="crash_round_status_number")]

    def __str__(self):
        return f"Round {self.number} · {self.status}"


class RoundBet(models.Model):
    """A player's bet on one round, one per round. The money moves through wallet.services."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CASHED_OUT = "cashed_out", "Cashed out"
        LOST = "lost", "Lost"

    round = models.ForeignKey(CrashRound, related_name="bets", on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="round_bets", on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    target = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    multiplier = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    payout = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Round bets"
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(fields=["round", "user"], name="unique_round_bet_user"),
        ]
        indexes = [models.Index(fields=["user", "-id"], name="round_bet_user_id")]

    def __str__(self):
        return f"{self.user} · {self.amount} LC · round {self.round_id}"


class CrashBotBet(models.Model):
    """A demo bot's bet in the live feed. It has no user, so it can't reach a wallet or the leaderboard.

    Only the current round's rows are kept.
    """

    round = models.ForeignKey(CrashRound, related_name="bot_bets", on_delete=models.CASCADE)
    name = models.CharField(max_length=30)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    target = models.DecimalField(max_digits=12, decimal_places=2)
    multiplier = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    payout = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        verbose_name_plural = "Crash bot bets"
        ordering = ["id"]

    def __str__(self):
        return f"{self.name} · {self.amount} LC"


class CrashBotSettings(models.Model):
    """The demo bots, one row edited in the admin. `load_sample` leaves it alone."""

    is_enabled = models.BooleanField(default=True)
    count = models.PositiveSmallIntegerField(default=8, help_text="How many bots bet in a round")
    min_bet = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("10.00"))
    max_bet = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("500.00"))
    names = models.TextField(default=DEFAULT_BOT_NAMES, help_text="One name per line")

    class Meta:
        verbose_name_plural = "Crash bot settings"
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(max_bet__gte=models.F("min_bet")), name="crash_bot_bet_range"),
        ]

    @classmethod
    def load(cls):
        return cls.objects.get_or_create(pk=1)[0]

    def name_list(self):
        return [name.strip()[:30] for name in self.names.splitlines() if name.strip()]

    def __str__(self):
        return "Crash bot settings"


class CrashPageLabel(models.Model):
    """Every text of the Neon Crash page in one language."""

    lang = models.CharField(max_length=10, choices=LANG_CHOICES, db_index=True)
    page_title = models.CharField(max_length=100)
    page_description = models.CharField(max_length=255)
    game_title = models.CharField(max_length=100)
    tab_manual = models.CharField(max_length=50)
    tab_auto = models.CharField(max_length=50)
    bet_amount = models.CharField(max_length=50)
    bet_half = models.CharField(max_length=10)
    bet_double = models.CharField(max_length=10)
    bet_plus = models.CharField(max_length=10)
    bet_max = models.CharField(max_length=10)
    auto_cash_out_at = models.CharField(max_length=50)
    place_bet = models.CharField(max_length=50)
    bet_placed = models.CharField(max_length=50)
    cash_out = models.CharField(max_length=50)
    cashed_out = models.CharField(max_length=100, help_text="{multiplier} is replaced with the multiplier")
    betting_status = models.CharField(max_length=100, help_text="{seconds} is replaced with the seconds left")
    flying_status = models.CharField(max_length=100)
    crashed_status = models.CharField(max_length=100, help_text="{multiplier} is replaced with the crash point")
    waiting_status = models.CharField(max_length=100)
    live_bets = models.CharField(max_length=50)
    players_count = models.CharField(max_length=50, help_text="{count} is replaced with the number")
    bet_lost = models.CharField(max_length=50)
    bot_badge = models.CharField(max_length=20)
    history_title = models.CharField(max_length=100)
    round_number = models.CharField(max_length=50, help_text="{number} is replaced with the round number")
    provably_fair = models.CharField(max_length=50)
    house_edge = models.CharField(max_length=50, help_text="{value} is replaced with the percentage")
    seed_label = models.CharField(max_length=50)
    seed_hash_label = models.CharField(max_length=50)
    commitment_label = models.CharField(max_length=50)
    connecting = models.CharField(max_length=100)
    server_unreachable = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = "Crash page labels"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["lang"], name="unique_crash_page_label_lang"),
        ]

    def __str__(self):
        return f"Crash page labels ({self.lang})"
