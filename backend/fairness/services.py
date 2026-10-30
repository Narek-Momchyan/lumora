from django.db import transaction
from django.utils import timezone

from .models import SeedPair


def active_seed_pair(user):
    pair, _ = SeedPair.objects.get_or_create(user=user, is_active=True)
    return pair


def _lock_active_pair(user):
    # If a rotation commits while we wait for the lock, the old pair is no longer active
    # (PostgreSQL re-checks the WHERE after the wait), so we lock the new one instead.
    # A bet must never use a server seed that was already revealed.
    for _ in range(3):
        active_seed_pair(user)
        pair = SeedPair.objects.select_for_update().filter(user=user, is_active=True).first()
        if pair is not None:
            return pair
    raise SeedPair.DoesNotExist("No active seed pair")


def next_nonce(user):
    """Reserve the next nonce for a bet. Returns (pair, nonce). Call inside the bet's transaction."""
    with transaction.atomic():
        pair = _lock_active_pair(user)
        nonce = pair.nonce
        pair.nonce += 1
        pair.save(update_fields=["nonce"])
        return pair, nonce


def rotate_seeds(user, client_seed=None):
    """Reveal the current server seed and start a new pair. Returns (revealed, active)."""
    with transaction.atomic():
        old = _lock_active_pair(user)
        old.is_active = False
        old.revealed_at = timezone.now()
        old.save(update_fields=["is_active", "revealed_at"])
        new = SeedPair(user=user)
        if client_seed:
            new.client_seed = client_seed
        new.save()
        return old, new
