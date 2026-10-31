from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

# No SVG: /media/ is served from the site's own origin, and an SVG can carry scripts.
IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp", "gif"]
MAX_IMAGE_SIZE_MB = 5


def validate_image_size(file):
    if getattr(file, "_committed", True):
        return
    if file.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"Image must be {MAX_IMAGE_SIZE_MB} MB or smaller.")


def is_image(head):
    return (
        head.startswith((b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"GIF87a", b"GIF89a"))
        or (head[:4] == b"RIFF" and head[8:12] == b"WEBP")
    )


def validate_image_content(file):
    """The extension can lie, so the file's first bytes must be a real image signature."""
    if getattr(file, "_committed", True):
        return
    head = file.read(12)
    file.seek(0)
    if not is_image(head):
        raise ValidationError("Upload a real JPG, PNG, WEBP or GIF image.")


IMAGE_VALIDATORS = [FileExtensionValidator(IMAGE_EXTENSIONS), validate_image_size, validate_image_content]

AUDIO_EXTENSIONS = ["mp3", "ogg", "wav"]
MAX_AUDIO_SIZE_MB = 10


def validate_audio_size(file):
    if getattr(file, "_committed", True):
        return
    if file.size > MAX_AUDIO_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"Audio must be {MAX_AUDIO_SIZE_MB} MB or smaller.")


def is_audio(head):
    return (
        head.startswith((b"ID3", b"OggS", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"))
        or (head[:4] == b"RIFF" and head[8:12] == b"WAVE")
    )


def validate_audio_content(file):
    if getattr(file, "_committed", True):
        return
    head = file.read(12)
    file.seek(0)
    if not is_audio(head):
        raise ValidationError("Upload a real MP3, OGG or WAV file.")


AUDIO_VALIDATORS = [FileExtensionValidator(AUDIO_EXTENSIONS), validate_audio_size, validate_audio_content]
