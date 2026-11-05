from django.core.management.base import BaseCommand, CommandError

from sports.live_runner import Runner, acquire_lock, default_client


class Command(BaseCommand):
    help = (
        "Keep the live scores fresh: one API-Football request every LIVE_POLL_SECONDS while one of our "
        "matches is in its 130-minute window (at most LIVE_DAILY_LIMIT a day). Without a key the "
        "delayed football-data.org score is shown."
    )

    def handle(self, *args, **options):
        if not acquire_lock():
            raise CommandError("Another run_live is already running.")
        client = default_client()
        source = "API-Football" if client else "football-data.org only (no API_FOOTBALL_KEY, or it is off)"
        self.stdout.write(self.style.SUCCESS(f"The live scores are running ({source}). Stop it with Ctrl+C."))
        try:
            Runner(client).run()
        except KeyboardInterrupt:
            self.stdout.write("Stopped.")
