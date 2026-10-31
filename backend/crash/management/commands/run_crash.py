from django.core.management.base import BaseCommand, CommandError

from crash.runner import Runner, acquire_lock


class Command(BaseCommand):
    help = "Run the live Neon Crash rounds. Keep one running next to the server, a second one refuses to start."

    def handle(self, *args, **options):
        if not acquire_lock():
            raise CommandError("Another run_crash is already running.")

        self.stdout.write(self.style.SUCCESS("Neon Crash is running. Stop it with Ctrl+C."))
        try:
            Runner().run()
        except KeyboardInterrupt:
            self.stdout.write("Stopped. The next run_crash continues the current round.")
