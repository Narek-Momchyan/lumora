from django.core.management.base import BaseCommand, CommandError

from roulette.runner import Runner, acquire_lock


class Command(BaseCommand):
    help = "Run the live Lumora Roulette rounds. Keep one running next to the server, a second one refuses to start."

    def handle(self, *args, **options):
        if not acquire_lock():
            raise CommandError("Another run_roulette is already running.")

        self.stdout.write(self.style.SUCCESS("Lumora Roulette is running. Stop it with Ctrl+C."))
        try:
            Runner().run()
        except KeyboardInterrupt:
            self.stdout.write("Stopped. The next run_roulette continues the current round.")
