"""Settle a slot spin: bet, roll, pay, all in one database transaction.

The paid spin and every free spin it opens are computed from one nonce, so a whole round can be
checked after the server seed is revealed. Nothing about a round is kept between requests.
"""

from django.db import transaction

from fairness.rng import float_stream
from fairness.services import next_nonce
from games.models import Game
from wallet import services as wallet_services
from . import engine
from .models import SlotSpin

GAME_SLUG = "zeus-legacy"


class SlotError(Exception):
    def __init__(self, code, text, **params):
        super().__init__(text)
        self.code = code
        self.params = params


def _playable_game(slug):
    game = Game.objects.filter(slug=slug).first() if slug == GAME_SLUG else None
    if game is None:
        raise SlotError("game_not_found", "This game doesn't exist.")
    if not game.is_active or not game.is_playable:
        raise SlotError("game_unavailable", "This game is not available right now.")
    return game


def play_spin(user, slug, amount, bonus_buy=False):
    """Raises SlotError for a bad bet and wallet.services.InsufficientFunds for a low balance."""
    game = _playable_game(slug)
    if not game.min_bet <= amount <= game.max_bet:
        raise SlotError(
            "bet_out_of_range",
            f"Bet must be between {game.min_bet} and {game.max_bet} LC.",
            min=game.min_bet,
            max=game.max_bet,
        )

    stake = engine.stake_for(amount, bonus_buy)
    contributions = {tier: stake * rate for tier, rate in engine.JACKPOT_RATES.items()}

    wallet = wallet_services.open_wallet(user)
    with transaction.atomic():
        pair, nonce = next_nonce(user)
        round_id = f"zeus:{pair.pk}:{nonce}"
        wallet_services.debit(wallet, stake, game=slug, round_id=round_id)
        wallet_services.add_to_jackpots(contributions, engine.JACKPOT_SEEDS)

        stream = float_stream(pair.server_seed, pair.client_seed, nonce)
        tier = engine.roll_jackpot(stake, next(stream))
        result = engine.play_round(stream, bonus_buy=bonus_buy)

        win = engine.win_amount(amount, result["total_win"])
        if win > 0:
            wallet_services.credit(wallet, win, game=slug, round_id=round_id)

        jackpot_win = 0
        if tier:
            paid = wallet_services.pay_jackpot(wallet, tier, engine.JACKPOT_SEEDS[tier], game=slug, round_id=round_id)
            jackpot_win = paid.amount

        return SlotSpin.objects.create(
            user=user,
            game=game,
            amount=amount,
            cost=stake,
            bonus_buy=bonus_buy,
            payout=win,
            free_spins_played=result["free_spins_played"],
            jackpot_tier=tier or "",
            jackpot_win=jackpot_win,
            result=result,
            server_seed_hash=pair.server_seed_hash,
            client_seed=pair.client_seed,
            nonce=nonce,
        )
