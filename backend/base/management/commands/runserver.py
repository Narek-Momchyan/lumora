from threading import Thread

from daphne.management.commands.runserver import Command as DaphneRunserver

from base import live
from crash import runner as crash_runner
from roulette import runner as roulette_runner


class Command(DaphneRunserver):
    """In development runserver also runs the live games, so that nothing else has to be started.

    inner_run is the process that autoreload restarts, so the rounds restart with the code.
    """

    def inner_run(self, *args, **options):
        for game in [crash_runner, roulette_runner]:
            Thread(target=live.run_forever, args=(game.acquire_lock, game.Runner), daemon=True).start()
        super().inner_run(*args, **options)
