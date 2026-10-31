from multiprocessing import Pool

from django.core.management.base import BaseCommand

from slots.simulation import simulate


def run_part(part):
    rounds, bonus_buy, first_nonce = part
    return simulate(rounds, bonus_buy=bonus_buy, first_nonce=first_nonce)


def merge(parts):
    """Averages the parts, weighted by their rounds."""
    rounds = sum(part["rounds"] for part in parts)
    total = dict(parts[0], rounds=rounds, best_round=max(part["best_round"] for part in parts))
    for key in ["rtp_game", "rtp_base_game", "rtp_jackpot", "rtp_total", "hit_rate"]:
        total[key] = sum(part[key] * part["rounds"] for part in parts) / rounds
    for key in ["bonuses", "free_spins", "max_wins"]:
        total[key] = sum(part[key] for part in parts)
    return total


class Command(BaseCommand):
    help = "Measure Zeus Legacy's RTP from slots/engine.py."

    def add_arguments(self, parser):
        parser.add_argument("--rounds", type=int, default=1_000_000)
        parser.add_argument("--bonus-buy", action="store_true")
        parser.add_argument("--workers", type=int, default=1)
        parser.add_argument("--parts", type=int, default=None, help="how many pieces to report one by one")

    def handle(self, *args, **options):
        workers = options["workers"]
        count = options["parts"] or workers
        size = options["rounds"] // count
        parts = [(size, options["bonus_buy"], i * size) for i in range(count)]
        with Pool(workers) as pool:
            results = pool.map(run_part, parts)

        for result in results:
            self.stdout.write(f"part: total RTP {result['rtp_total']:.2f}%")
        total = merge(results)
        for key, value in total.items():
            self.stdout.write(f"{key}: {value:.4f}" if isinstance(value, float) else f"{key}: {value}")
