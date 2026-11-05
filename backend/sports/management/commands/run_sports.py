from django.core.management.base import BaseCommand, CommandError

from sports import services
from sports.runner import Runner, acquire_lock


class Command(BaseCommand):
    help = "Keep the football data fresh: a full sync daily, today's matches every few minutes on match days."

    def handle(self, *args, **options):
        if not acquire_lock():
            raise CommandError("Another run_sports is already running.")
        try:
            client = services.default_client()
        except RuntimeError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS("The football sync is running. Stop it with Ctrl+C."))
        try:
            Runner(client).run()
        except KeyboardInterrupt:
            self.stdout.write("Stopped.")
