"""Provably fair randomness shared by every game (commit-reveal).

1. The server makes a secret server_seed and shows the player only its SHA-256 hash.
2. The player has a client_seed (random by default, can be changed on rotation).
3. Every bet uses the next nonce: 0, 1, 2 ...
4. Result = HMAC_SHA256(key=server_seed, msg=f"{client_seed}:{nonce}:{cursor}") turned into floats.
5. Rotating the seeds reveals the old server_seed, so anyone can recompute every past result
   and check that the seed matches the hash shown before the bets.

Seeds come from the `secrets` module. Never use `random` for anything that decides a result.
"""

import hashlib
import hmac
import secrets

FLOAT_BITS = 52


def new_server_seed():
    return secrets.token_hex(32)


def new_client_seed():
    return secrets.token_hex(8)


def hash_seed(server_seed):
    return hashlib.sha256(server_seed.encode()).hexdigest()


def float_stream(server_seed, client_seed, nonce):
    """Endless stream of uniform floats in [0, 1) for one bet (slots need many per spin)."""
    cursor = 0
    while True:
        message = f"{client_seed}:{nonce}:{cursor}".encode()
        digest = hmac.new(server_seed.encode(), message, hashlib.sha256).digest()
        # 32 bytes = 4 floats of 8 bytes each; the top 52 bits of each make the float.
        for i in range(0, 32, 8):
            value = int.from_bytes(digest[i : i + 8], "big") >> (64 - FLOAT_BITS)
            yield value / (1 << FLOAT_BITS)
        cursor += 1


def first_float(server_seed, client_seed, nonce):
    return next(float_stream(server_seed, client_seed, nonce))
