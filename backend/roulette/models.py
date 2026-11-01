from decimal import Decimal

from django.conf import settings
from django.db import models

from base.constants import LANG_CHOICES
from crash.models import DEFAULT_BOT_NAMES
from fairness.models import HashChain


class RouletteChain(HashChain):
    class Meta:
        verbose_name_plural = "Roulette chains"
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(fields=["commitment"], name="unique_roulette_chain_commitment"),
        ]


class RouletteRound(models.Model):
    """One shared spin. `result` stays secret until the spin starts, and `seed` until it is settled."""

    class Status(models.TextChoices):
        BETTING = "betting", "Betting"
        SPINNING = "spinning", "Spinning"
        SETTLED = "settled", "Settled"

    number = models.PositiveBigIntegerField()
    chain = models.ForeignKey(RouletteChain, related_name="rounds", on_delete=models.PROTECT)
    position = models.PositiveIntegerField(help_text="Place in the chain, the first round is 0")
    seed = models.CharField(max_length=64)
    seed_hash = models.CharField(max_length=64)
    result = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.BETTING)
    betting_ends_at = models.DateTimeField()
    spin_started_at = models.DateTimeField(null=True, blank=True)
    settled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Roulette rounds"
        ordering = ["-number"]
        constraints = [
            models.UniqueConstraint(fields=["number"], name="unique_roulette_round_number"),
            models.UniqueConstraint(fields=["chain", "position"], name="unique_roulette_round_chain_position"),
        ]
        indexes = [models.Index(fields=["status", "-number"], name="roulette_round_status_number")]

    def __str__(self):
        return f"Round {self.number} · {self.status}"


class RouletteSlip(models.Model):
    """One "Place bets": its lines are charged with one debit and win with one credit."""

    round = models.ForeignKey(RouletteRound, related_name="slips", on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="roulette_slips", on_delete=models.CASCADE)
    key = models.CharField(max_length=36, help_text="Made by the client: a repeated request finds this slip")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payout = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Roulette slips"
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(fields=["user", "key"], name="unique_roulette_slip_user_key"),
        ]
        indexes = [models.Index(fields=["user", "-id"], name="roulette_slip_user_id")]

    def __str__(self):
        return f"{self.user} · {self.amount} LC · round {self.round_id}"


class RouletteLine(models.Model):
    """One bet of a slip, for example Split 8 / 11, 5 LC."""

    slip = models.ForeignKey(RouletteSlip, related_name="lines", on_delete=models.CASCADE)
    bet_type = models.CharField(max_length=20)
    value = models.JSONField(default=list, blank=True)
    multiplier = models.PositiveSmallIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payout = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        verbose_name_plural = "Roulette lines"
        ordering = ["id"]

    def __str__(self):
        return f"{self.bet_type} {self.value} · {self.amount} LC"


class RouletteBotBet(models.Model):
    """A demo bot's bets at the table. It has no user, so it can't reach a wallet or the leaderboard.

    Only the current round's rows are kept.
    """

    round = models.ForeignKey(RouletteRound, related_name="bot_bets", on_delete=models.CASCADE)
    name = models.CharField(max_length=30)
    lines = models.JSONField(default=list, help_text='[{"bet_type": "red", "value": [], "amount": "50.00"}]')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payout = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        verbose_name_plural = "Roulette bot bets"
        ordering = ["id"]

    def __str__(self):
        return f"{self.name} · {self.amount} LC"


class RouletteBotSettings(models.Model):
    """The demo bots, one row edited in the admin. `load_sample` leaves it alone."""

    is_enabled = models.BooleanField(default=True)
    count = models.PositiveSmallIntegerField(default=8, help_text="How many bots bet in a round")
    min_bet = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("10.00"))
    max_bet = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("500.00"))
    names = models.TextField(default=DEFAULT_BOT_NAMES, help_text="One name per line")

    class Meta:
        verbose_name_plural = "Roulette bot settings"
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(max_bet__gte=models.F("min_bet")), name="roulette_bot_bet_range"
            ),
        ]

    @classmethod
    def load(cls):
        return cls.objects.get_or_create(pk=1)[0]

    def name_list(self):
        return [name.strip()[:30] for name in self.names.splitlines() if name.strip()]

    def __str__(self):
        return "Roulette bot settings"


class RoulettePageLabel(models.Model):
    """Every text of the Lumora Roulette page in one language, with the names of the bets."""

    lang = models.CharField(max_length=10, choices=LANG_CHOICES, db_index=True)
    page_title = models.CharField(max_length=100)
    page_description = models.CharField(max_length=255)
    game_title = models.CharField(max_length=100)
    live = models.CharField(max_length=20)
    players_count = models.CharField(max_length=50, help_text="{count} is replaced with the number")
    bets_close_in = models.CharField(max_length=50)
    place_your_bets = models.CharField(max_length=100)
    no_more_bets = models.CharField(max_length=50)
    spinning = models.CharField(max_length=50)
    result_in = models.CharField(max_length=50, help_text="{seconds} is replaced with the seconds left")
    last_result = models.CharField(max_length=50)
    winning_number = models.CharField(max_length=50)
    you_won = models.CharField(max_length=50)
    net_win = models.CharField(max_length=50, help_text="{amount} is replaced with the net win")
    bets_won = models.CharField(max_length=100, help_text="{won} and {total} are replaced with the numbers")
    your_bets = models.CharField(max_length=50)
    bets_count = models.CharField(max_length=50, help_text="{count} is replaced with the number")
    chip_value = models.CharField(max_length=50)
    undo = models.CharField(max_length=30)
    clear = models.CharField(max_length=30)
    double = models.CharField(max_length=10)
    rebet = models.CharField(max_length=30)
    total_bet = models.CharField(max_length=50)
    total_win = models.CharField(max_length=50)
    place_bets = models.CharField(max_length=50)
    bets_closed = models.CharField(max_length=50)
    live_table = models.CharField(max_length=50)
    next_round_in = models.CharField(max_length=50, help_text="{seconds} is replaced with the seconds left")
    you_badge = models.CharField(max_length=20)
    bot_badge = models.CharField(max_length=20)
    round_number = models.CharField(max_length=50, help_text="{number} is replaced with the round number")
    provably_fair = models.CharField(max_length=50)
    house_edge = models.CharField(max_length=50, help_text="{value} is replaced with the percentage")
    seed_label = models.CharField(max_length=50)
    seed_hash_label = models.CharField(max_length=50)
    commitment_label = models.CharField(max_length=50)
    connecting = models.CharField(max_length=100)
    server_unreachable = models.CharField(max_length=255)
    color_red = models.CharField(max_length=30)
    color_black = models.CharField(max_length=30)
    color_green = models.CharField(max_length=30)
    bet_straight = models.CharField(max_length=30)
    bet_split = models.CharField(max_length=30)
    bet_street = models.CharField(max_length=30)
    bet_trio = models.CharField(max_length=30)
    bet_corner = models.CharField(max_length=30)
    bet_six_line = models.CharField(max_length=30)
    bet_first_four = models.CharField(max_length=30)
    bet_red = models.CharField(max_length=30)
    bet_black = models.CharField(max_length=30)
    bet_even = models.CharField(max_length=30)
    bet_odd = models.CharField(max_length=30)
    bet_low = models.CharField(max_length=30)
    bet_high = models.CharField(max_length=30)
    bet_dozen_1 = models.CharField(max_length=30)
    bet_dozen_2 = models.CharField(max_length=30)
    bet_dozen_3 = models.CharField(max_length=30)
    bet_column = models.CharField(max_length=30, help_text="{number} is replaced with the column")
    bet_column_short = models.CharField(max_length=30)

    class Meta:
        verbose_name_plural = "Roulette page labels"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["lang"], name="unique_roulette_page_label_lang"),
        ]

    def __str__(self):
        return f"Roulette page labels ({self.lang})"
