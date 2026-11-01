from django.conf import settings
from django.db import models

from .rng import hash_seed, new_client_seed, new_server_seed


class HashChain(models.Model):
    """A hash chain of round seeds for a game whose rounds are shared by all players.

    `last_seed` never leaves the server. `commitment` is the SHA-256 of the first round's seed,
    it is public, and every revealed seed must hash down to it.
    """

    last_seed = models.CharField(max_length=64)
    commitment = models.CharField(max_length=64)
    length = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"Chain {self.pk} · {self.commitment[:12]}"


class SeedPair(models.Model):
    """A player's provably fair seeds. One active pair per player; rotating reveals the old one."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="seed_pairs", on_delete=models.CASCADE)
    server_seed = models.CharField(max_length=64, default=new_server_seed)
    server_seed_hash = models.CharField(max_length=64, editable=False)
    client_seed = models.CharField(max_length=64, default=new_client_seed)
    nonce = models.PositiveIntegerField(default=0)  # next nonce; bets used 0 .. nonce-1
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revealed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Seed pairs"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"], condition=models.Q(is_active=True), name="one_active_seed_pair_per_user"
            ),
        ]

    def save(self, *args, **kwargs):
        self.server_seed_hash = hash_seed(self.server_seed)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} · {self.server_seed_hash[:12]}"
