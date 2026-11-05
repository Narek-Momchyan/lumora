from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from base.sample import SAMPLE_DB, add_missing, clear_sample, load_sample, read_sample, reset_sequences


class Command(BaseCommand):
    help = (
        "Add the rows of base/sample_db.json that are missing (texts edited in the admin stay). "
        "--reset replaces all texts, the logo and the languages. Never touches players or money."
    )

    def add_arguments(self, parser):
        parser.add_argument("--path", default=str(SAMPLE_DB))
        parser.add_argument("--reset", action="store_true", help="Delete the content and load the sample again")

    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.exists():
            raise CommandError(f"{path} not found")

        data = read_sample(path)
        with transaction.atomic():
            if options["reset"]:
                clear_sample()
                load_sample(data)
                reset_sequences()
                message = f"Replaced the content with {len(data)} collections from {path}"
            else:
                message = f"Added {add_missing(data)} missing rows from {path}"

        self.stdout.write(self.style.SUCCESS(message))
