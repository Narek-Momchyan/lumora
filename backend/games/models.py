from decimal import Decimal

from django.db import models

from base.constants import LANG_CHOICES
from base.fields import AUDIO_VALIDATORS, IMAGE_VALIDATORS


class Game(models.Model):
    class Category(models.TextChoices):
        SLOT = "slot", "Slot"
        CRASH = "crash", "Crash"
        TABLE = "table", "Table"
        INSTANT = "instant", "Instant"
        SPORTS = "sports", "Sports"

    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=60)
    category = models.CharField(max_length=16, choices=Category.choices, db_index=True)
    rtp = models.DecimalField(max_digits=5, decimal_places=2, help_text="Theoretical RTP in percent")
    min_bet = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))
    max_bet = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("10000.00"))
    is_active = models.BooleanField(default=False, help_text="Only active games are in the API")
    is_playable = models.BooleanField(default=False, help_text="Off: the lobby shows the game as coming soon")
    is_featured = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=100)
    image = models.FileField(upload_to="images/games/", max_length=255, blank=True, validators=IMAGE_VALIDATORS)

    class Meta:
        verbose_name_plural = "Games"
        ordering = ["sort_order", "title"]

    def __str__(self):
        return self.title


class GameCategory(models.Model):
    """A category's names in one language: `filter_label` titles the filtered lobby, `card_label` is on cards."""

    lang = models.CharField(max_length=10, choices=LANG_CHOICES, db_index=True)
    code = models.CharField(max_length=16, choices=Game.Category.choices)
    filter_label = models.CharField(max_length=50)
    card_label = models.CharField(max_length=50)
    order = models.PositiveSmallIntegerField(default=0)
    is_soon = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Game categories"
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["lang", "code"], name="unique_game_category_lang_code"),
        ]

    def __str__(self):
        return f"{self.filter_label} ({self.lang})"


class LobbyPageLabel(models.Model):
    """Every text of the lobby page in one language."""

    lang = models.CharField(max_length=10, choices=LANG_CHOICES, db_index=True)
    page_title = models.CharField(max_length=100)
    page_description = models.CharField(max_length=255)
    bonus_eyebrow = models.CharField(max_length=50)
    bonus_title = models.CharField(max_length=100)
    bonus_text = models.CharField(max_length=255)
    bonus_claim_button = models.CharField(max_length=50)
    bonus_claiming = models.CharField(max_length=50)
    bonus_claimed = models.CharField(max_length=100)
    bonus_next = models.CharField(max_length=100, help_text="{time} is replaced with the date and time")
    section_popular = models.CharField(max_length=100)
    section_all = models.CharField(max_length=100)
    soon_badge = models.CharField(max_length=30)
    rtp_label = models.CharField(max_length=20)
    no_results = models.CharField(max_length=255)
    server_unreachable = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = "Lobby page labels"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["lang"], name="unique_lobby_page_label_lang"),
        ]

    def __str__(self):
        return f"Lobby page labels ({self.lang})"


class GameSound(models.Model):
    """A sound of Neon Crash or Lumora Roulette, uploaded in the admin. The pages play only the sounds that
    have a file; a code without one is silently skipped. A key shared by both games (round start, bet placed,
    win, lose) has one file for both."""

    class Code(models.TextChoices):
        CRASH_FLIGHT = "crash_flight", "Crash: the multiplier climbs (loops during the flight)"
        CRASH_BOOM = "crash_boom", "Crash: the crash"
        CASH_OUT = "cash_out", "Crash: my cash-out"
        BET_PLACED = "bet_placed", "My bet is placed (both games)"
        ROUND_START = "round_start", "Betting opens (both games)"
        ROULETTE_SPIN = "roulette_spin", "Roulette: the wheel starts"
        ROULETTE_BALL_DROP = "roulette_ball_drop", "Roulette: the ball drops (last 1.6 s of the spin)"
        WIN = "win", "I won (both games)"
        LOSE = "lose", "I lost (both games)"

    code = models.CharField(max_length=30, choices=Code.choices)
    file = models.FileField(
        upload_to="sounds/games/", max_length=255, blank=True, validators=AUDIO_VALIDATORS,
        help_text="MP3, OGG or WAV, at most 10 MB. Without a file the sound is skipped",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Game sounds"
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["code"], name="unique_game_sound_code")]

    def __str__(self):
        return self.get_code_display()
