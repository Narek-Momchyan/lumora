from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

from .svg import is_safe_svg

# Plain images. SVG only through IMAGE_OR_SVG_VALIDATORS: /media/ is served from the site's own
# origin, and an SVG can carry scripts, so it must pass base.svg first.
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


def validate_image_or_svg_content(file):
    """Like validate_image_content, plus an SVG that is already safe (see base.svg)."""
    if getattr(file, "_committed", True):
        return
    if file.name.lower().endswith(".svg"):
        data = file.read()
        file.seek(0)
        if not is_safe_svg(data):
            raise ValidationError("This SVG has scripts, links or parts we don't allow. Upload a plain drawing.")
        return
    validate_image_content(file)


# Icons and crests may also be SVG: drawn in one colour by the frontend, sharp at any size.
IMAGE_OR_SVG_VALIDATORS = [
    FileExtensionValidator([*IMAGE_EXTENSIONS, "svg"]),
    validate_image_size,
    validate_image_or_svg_content,
]

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
