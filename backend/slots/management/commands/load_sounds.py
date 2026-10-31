from urllib.error import URLError
from urllib.request import Request, urlopen

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from base.fields import MAX_AUDIO_SIZE_MB
from slots.models import SlotSound

MIXKIT_URL = "https://assets.mixkit.co/active_storage/sfx/{id}/{id}-preview.mp3"
TIMEOUT_SECONDS = 30

# The Mixkit sounds of the original Zeus Legacy.
MIXKIT_IDS = {
    SlotSound.Code.STONE_TUMBLE: 2568,
    SlotSound.Code.SPARKLE_WIN: 2013,
    SlotSound.Code.LIGHTNING_HIT: 1287,
    SlotSound.Code.EPIC_DROP: 632,
    SlotSound.Code.FREE_SPINS_THEME: 2290,
    SlotSound.Code.BIG_WIN: 1993,
    SlotSound.Code.MEGA_WIN: 2004,
    SlotSound.Code.ULTRA_WIN: 2012,
    SlotSound.Code.SYMBOL_EXPLODE: 1105,
    SlotSound.Code.COLLECT_MULTIPLIER: 2019,
    SlotSound.Code.WIN_TICK: 2013,
    SlotSound.Code.SCATTER_IMPACT: 2020,
}


def download(mixkit_id):
    request = Request(MIXKIT_URL.format(id=mixkit_id), headers={"User-Agent": "lumora-load-sounds"})
    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        # One byte over the limit is enough for the model's validator to refuse the file.
        return response.read(MAX_AUDIO_SIZE_MB * 1024 * 1024 + 1)


class Command(BaseCommand):
    help = "Download the Zeus Legacy sounds into media/sounds/zeus/ and create their SlotSound rows."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Also replace sounds that already have a file.")

    def handle(self, *args, force, **options):
        failed = []
        for code, mixkit_id in MIXKIT_IDS.items():
            sound = SlotSound.objects.filter(code=code).first() or SlotSound(code=code)
            if sound.file and not force:
                self.stdout.write(f"{code}: kept")
                continue

            try:
                self.load(sound, code, mixkit_id)
            except (OSError, URLError, ValidationError) as error:
                failed.append(code)
                self.stderr.write(f"{code}: {error}")
            else:
                self.stdout.write(f"{code}: loaded")

        if failed:
            raise CommandError(f"Not loaded: {', '.join(failed)}")

    def load(self, sound, code, mixkit_id):
        content = download(mixkit_id)
        old_file = sound.file.name
        storage = sound.file.storage
        sound.file = ContentFile(content, name=f"{code}.mp3")
        sound.full_clean()
        sound.save()
        if old_file:
            storage.delete(old_file)
