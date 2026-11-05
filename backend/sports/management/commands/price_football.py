from django.core.management.base import BaseCommand

from sports import services


class Command(BaseCommand):
    help = "Settle finished matches, fit the odds model on them and price the next 14 days (no provider requests)."

    def handle(self, *args, **options):
        model = services.after_sync()
        line = f"Model fitted on {model.matches_used} matches (rho {model.rho}), {model.priced_matches} matches priced."
        self.stdout.write(self.style.SUCCESS(line))
