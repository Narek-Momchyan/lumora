from django.core.management.base import BaseCommand

from sports import engine
from sports.odds import finished_results


class Command(BaseCommand):
    help = "Walk-forward backtest of the odds model on the finished matches: 1X2 log loss and Brier vs a baseline."

    def add_arguments(self, parser):
        parser.add_argument("--min-history", type=int, default=60, help="Matches before the first prediction")

    def handle(self, *args, **options):
        report = engine.backtest(finished_results(), min_history=options["min_history"])
        if not report["matches"]:
            self.stdout.write("Not enough finished matches yet.")
            return
        self.stdout.write(f"Predicted {report['matches']} matches, each only from the days before it.")
        self.stdout.write("                 log loss   Brier")
        self.stdout.write(f"Lumora model     {report['model_log_loss']:.4f}     {report['model_brier']:.4f}")
        self.stdout.write(f"League baseline  {report['baseline_log_loss']:.4f}     {report['baseline_brier']:.4f}")
        self.stdout.write("Lower is better. A uniform guess (1/3 each) scores 1.0986 and 0.6667.")
