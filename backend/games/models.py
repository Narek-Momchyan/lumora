from decimal import Decimal

from django.db import models


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
    is_featured = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        verbose_name_plural = "Games"
        ordering = ["sort_order", "title"]

    def __str__(self):
        return self.title
