from decimal import Decimal

from django.conf import settings
from django.db import models

from base.constants import LANG_CHOICES
from base.fields import AUDIO_VALIDATORS, IMAGE_VALIDATORS
from games.models import Game


class SlotSymbol(models.Model):
    """A symbol's picture. The paytable and weights stay in engine.py: the admin can't change maths."""

    code = models.CharField(max_length=20)
    image = models.FileField(upload_to="images/zeus/symbols/", max_length=255, blank=True, validators=IMAGE_VALIDATORS)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name_plural = "Slot symbols"
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="unique_slot_symbol_code"),
        ]

    def __str__(self):
        return self.code


class SlotSymbolName(models.Model):
    symbol = models.ForeignKey(SlotSymbol, to_field="code", related_name="names", on_delete=models.CASCADE)
    lang = models.CharField(max_length=10, choices=LANG_CHOICES, db_index=True)
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "Slot symbol names"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["symbol", "lang"], name="unique_slot_symbol_name_lang"),
        ]

    def __str__(self):
        return f"{self.name} ({self.lang})"


class SlotSound(models.Model):
    """A game sound, uploaded in the admin. The frontend plays only the ones that have a file."""

    class Code(models.TextChoices):
        STONE_TUMBLE = "stone_tumble", "Stones fall"
        SPARKLE_WIN = "sparkle_win", "A win appears"
        LIGHTNING_HIT = "lightning_hit", "Lightning"
        EPIC_DROP = "epic_drop", "A big drop"
        FREE_SPINS_THEME = "free_spins_theme", "Free spins music"
        BIG_WIN = "big_win", "Big win"
        MEGA_WIN = "mega_win", "Mega win"
        ULTRA_WIN = "ultra_win", "Ultra win"
        SYMBOL_EXPLODE = "symbol_explode", "A symbol explodes"
        COLLECT_MULTIPLIER = "collect_multiplier", "A multiplier is collected"
        WIN_TICK = "win_tick", "The win counts up"
        SCATTER_IMPACT = "scatter_impact", "A scatter lands"

    code = models.CharField(max_length=30, choices=Code.choices)
    file = models.FileField(upload_to="sounds/zeus/", max_length=255, blank=True, validators=AUDIO_VALIDATORS)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Slot sounds"
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="unique_slot_sound_code"),
        ]

    def __str__(self):
        return self.code


class ZeusPageLabel(models.Model):
    """Every text of the Zeus Legacy page in one language."""

    lang = models.CharField(max_length=10, choices=LANG_CHOICES, db_index=True)
    page_title = models.CharField(max_length=100)
    page_description = models.CharField(max_length=255)
    game_title = models.CharField(max_length=100)
    tagline = models.CharField(max_length=255)
    free_spins_title = models.CharField(max_length=100)
    free_spins_left = models.CharField(max_length=100, help_text="{count} is replaced with the number")
    tumble = models.CharField(max_length=50, help_text="{count} is replaced with the number")
    multiplier_total = models.CharField(max_length=50)
    multiplier_collected = models.CharField(max_length=50)
    balance = models.CharField(max_length=50)
    last_win = models.CharField(max_length=50)
    win = models.CharField(max_length=50)
    bet = models.CharField(max_length=50)
    bonus_bet = models.CharField(max_length=50)
    speed_mode = models.CharField(max_length=50)
    speed_normal = models.CharField(max_length=50)
    speed_turbo = models.CharField(max_length=50)
    speed_instant = models.CharField(max_length=50)
    spin = models.CharField(max_length=50)
    buy_bonus = models.CharField(max_length=50)
    auto = models.CharField(max_length=50)
    auto_spinning = models.CharField(max_length=50)
    loading = models.CharField(max_length=50)
    loading_tagline = models.CharField(max_length=100)
    ready = models.CharField(max_length=50)
    bonus_trigger = models.CharField(max_length=50)
    congratulations = models.CharField(max_length=100)
    total_win = models.CharField(max_length=50)
    collect = models.CharField(max_length=50)
    win_winning = models.CharField(max_length=50)
    win_big = models.CharField(max_length=50)
    win_super = models.CharField(max_length=50)
    win_mega = models.CharField(max_length=50)
    win_ultra = models.CharField(max_length=50)
    win_max = models.CharField(max_length=50)
    jackpot_mini = models.CharField(max_length=30)
    jackpot_minor = models.CharField(max_length=30)
    jackpot_major = models.CharField(max_length=30)
    jackpot_grand = models.CharField(max_length=30)
    jackpot_won = models.CharField(max_length=100, help_text="{tier} is replaced with the jackpot's name")
    server_unreachable = models.CharField(max_length=255)
    free_spins_won = models.CharField(max_length=100, help_text="{count} is replaced with the number")
    buy_bonus_title = models.CharField(max_length=100)
    buy_bonus_text = models.CharField(max_length=255, help_text="{amount} is replaced with the price")
    buy_bonus_confirm = models.CharField(max_length=50)
    cancel = models.CharField(max_length=50)
    stop = models.CharField(max_length=50)
    skip = models.CharField(max_length=50)
    auto_spins_left = models.CharField(max_length=50, help_text="{count} is replaced with the number")
    auto_menu_label = models.CharField(max_length=100)
    mute = models.CharField(max_length=50)
    unmute = models.CharField(max_length=50)
    bet_lower = models.CharField(max_length=50)
    bet_raise = models.CharField(max_length=50)
    jackpots_label = models.CharField(max_length=50)
    history_title = models.CharField(max_length=100)
    history_empty = models.CharField(max_length=255)
    history_time = models.CharField(max_length=50)
    history_cost = models.CharField(max_length=50)
    history_win = models.CharField(max_length=50)
    history_bonus_buy = models.CharField(max_length=50)
    history_free_spins = models.CharField(max_length=50)
    history_seed_hash = models.CharField(max_length=50)
    history_client_seed = models.CharField(max_length=50)
    history_nonce = models.CharField(max_length=50)

    class Meta:
        verbose_name_plural = "Zeus page labels"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["lang"], name="unique_zeus_page_label_lang"),
        ]

    def __str__(self):
        return f"Zeus page labels ({self.lang})"


class SlotSpin(models.Model):
    """One paid spin with all its free spins. `result` lets the frontend replay every tumble."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="slot_spins", on_delete=models.CASCADE)
    game = models.ForeignKey(Game, related_name="slot_spins", on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    cost = models.DecimalField(max_digits=12, decimal_places=2, help_text="What was charged: the bet, or 100x for a bonus buy")
    bonus_buy = models.BooleanField(default=False)
    payout = models.DecimalField(max_digits=14, decimal_places=2)
    free_spins_played = models.PositiveIntegerField(default=0)
    jackpot_tier = models.CharField(max_length=8, blank=True)
    jackpot_win = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    result = models.JSONField()
    server_seed_hash = models.CharField(max_length=64)
    client_seed = models.CharField(max_length=64)
    nonce = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Slot spins"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["user", "-created_at"], name="slot_spin_user_created")]

    def __str__(self):
        return f"{self.user} · {self.game} · {self.cost} LC"
