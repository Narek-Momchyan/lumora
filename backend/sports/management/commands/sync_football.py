from django.core.management.base import BaseCommand, CommandError

from sports import services
from sports.models import SyncRun


class Command(BaseCommand):
    help = "Sync football data from football-data.org: today's matches and tables, or the whole season with --full."

    def add_arguments(self, parser):
        parser.add_argument("--competition", action="append", help="Only this code (PL, PD, SA, BL1, FL1, CL); repeatable")
        parser.add_argument("--full", action="store_true", help="The whole season: teams, crests, every match, tables")

    def handle(self, *args, **options):
        try:
            client = services.default_client()
        except RuntimeError as exc:
            raise CommandError(str(exc)) from exc

        kind = SyncRun.Kind.FULL if options["full"] else SyncRun.Kind.TODAY
        runs = services.run_sync(client, kind, codes=options["competition"])
        if not runs:
            raise CommandError("No active competition matches. Check the codes and Competition.is_active in the admin.")

        for run in runs:
            line = f"{run.competition.code}: {run.requests} requests, {run.created} created, {run.updated} updated"
            if run.ok:
                self.stdout.write(self.style.SUCCESS(line))
            else:
                self.stdout.write(self.style.ERROR(f"{line} - {run.errors}"))
            if run.ok and run.errors:
                self.stdout.write(self.style.WARNING(run.errors))

        model = services.after_sync()
        self.stdout.write(
            f"Settled finished matches; model fitted on {model.matches_used} matches, "
            f"{model.priced_matches} matches priced."
        )
