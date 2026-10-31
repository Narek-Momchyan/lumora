from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from base.sample import SAMPLE_DB, clear_sample, load_sample, read_sample, reset_sequences


class Command(BaseCommand):
    help = "Load base/sample_db.json into the database (replaces texts, logo and languages, never players or money)."

    def add_arguments(self, parser):
        parser.add_argument("--path", default=str(SAMPLE_DB))

    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.exists():
            raise CommandError(f"{path} not found")

        data = read_sample(path)
        with transaction.atomic():
            clear_sample()
            load_sample(data)
            reset_sequences()

        self.stdout.write(self.style.SUCCESS(f"Loaded {len(data)} collections from {path}"))
