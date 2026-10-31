"""Measures Zeus Legacy's RTP from engine.py. Used by the slow test and `manage.py simulate_zeus`."""

from decimal import Decimal

from fairness.rng import float_stream
from . import engine

BET = Decimal("1")


def simulate(rounds, *, bonus_buy=False, server_seed="sim-seed", client_seed="sim-client", first_nonce=0):
    """Plays paid rounds the way services.play_spin does. RTPs are in percent of the money staked."""
    stake = engine.stake_for(BET, bonus_buy)
    seeds = {tier: float(seed) for tier, seed in engine.JACKPOT_SEEDS.items()}
    rates = {tier: float(rate) for tier, rate in engine.JACKPOT_RATES.items()}
    pools = dict(seeds)

    game_win = 0  # in hundredths of the bet
    jackpot_win = 0.0
    base_game_win = 0
    hits = 0
    bonuses = 0
    free_spins = 0
    max_wins = 0
    best_round = 0

    for nonce in range(first_nonce, first_nonce + rounds):
        stream = float_stream(server_seed, client_seed, nonce)
        pools = {tier: pool + float(stake) * rates[tier] for tier, pool in pools.items()}
        tier = engine.roll_jackpot(stake, next(stream))
        if tier:
            jackpot_win += pools[tier]
            pools[tier] = seeds[tier]

        result = engine.play_round(stream, bonus_buy=bonus_buy)
        first = result["spins"][0]
        game_win += result["total_win"]
        base_game_win += first["win"]
        hits += first["win"] > 0
        bonuses += first["free_spins_awarded"] > 0
        free_spins += result["free_spins_played"]
        max_wins += sum(spin["is_max_win"] for spin in result["spins"])
        best_round = max(best_round, result["total_win"])

    staked = rounds * float(stake)
    return {
        "rounds": rounds,
        "bonus_buy": bonus_buy,
        "rtp_game": game_win / 100 / staked * 100,
        "rtp_base_game": base_game_win / 100 / staked * 100,
        "rtp_jackpot": jackpot_win / staked * 100,
        "rtp_total": (game_win / 100 + jackpot_win) / staked * 100,
        "hit_rate": hits / rounds * 100,
        "bonuses": bonuses,
        "free_spins": free_spins,
        "max_wins": max_wins,
        "best_round": best_round / 100,
    }
