"""How a player is shown to other players: never by email, and never by user id.

User ids are sequential, so an id in a public feed shows how many players there are and lets anyone walk
through them, and an email prefix is a piece of someone's address. Public feeds therefore use the display
name, or, for a player who has none, a stable name made from a keyed hash, and a keyed hash instead of the
id wherever the page needs to tell players apart (a roulette seat). The hash uses SECRET_KEY, so nobody
can compute it from an id; the player can read their own in /api/me (`public_id`).
"""

import hashlib
import hmac

from django.conf import settings

ANONYMOUS = "Player"  # the word before the short code of a player without a display name


def public_id(user_id):
    """12 hex characters that identify a player in public feeds, stable and not derivable from the id."""
    key = settings.SECRET_KEY.encode()
    return hmac.new(key, f"public-id:{user_id}".encode(), hashlib.sha256).hexdigest()[:12]


def public_name(display_name, user_id):
    """The display name, else "Player a1b2c3". Takes plain values, so it works on `.values()` rows too."""
    return display_name or f"{ANONYMOUS} {public_id(user_id)[:6]}"
