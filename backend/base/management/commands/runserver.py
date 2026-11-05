from threading import Thread

from daphne.management.commands.runserver import Command as DaphneRunserver
from django.conf import settings

from base import live
from crash import runner as crash_runner
from roulette import runner as roulette_runner
from sports import runner as sports_runner


class Command(DaphneRunserver):
    """In development runserver also runs the live games and, when FOOTBALL_DATA_TOKEN is set, the
    football sync, so that nothing else has to be started.

    inner_run is the process that autoreload restarts, so the rounds restart with the code.
    """

    def inner_run(self, *args, **options):
        for game in [crash_runner, roulette_runner]:
            Thread(target=live.run_forever, args=(game.acquire_lock, game.Runner), daemon=True).start()
        if settings.FOOTBALL_DATA_TOKEN:
            sports = (sports_runner.acquire_lock, sports_runner.Runner)
            Thread(target=live.run_forever, args=sports, daemon=True).start()
        else:
            self.stdout.write("Football sync is off: set FOOTBALL_DATA_TOKEN in backend/.env to turn it on.")
        super().inner_run(*args, **options)
