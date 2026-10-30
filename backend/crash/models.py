from django.conf import settings
from django.db import models


class CrashBet(models.Model):
    """One settled Neon Crash round. Keeps everything needed to verify it later."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="crash_bets", on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    target = models.DecimalField(max_digits=12, decimal_places=2)
    crash_point = models.DecimalField(max_digits=12, decimal_places=2)
    payout = models.DecimalField(max_digits=14, decimal_places=2)
    server_seed_hash = models.CharField(max_length=64)
    client_seed = models.CharField(max_length=64)
    nonce = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Crash bets"
        ordering = ["-created_at", "-id"]

    @property
    def won(self):
        return self.payout > 0

    def __str__(self):
        return f"{self.user} · {self.amount} LC @ {self.target}x"
