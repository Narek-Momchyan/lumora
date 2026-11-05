"""A club's crest file and badge colours from what the provider gives."""

from pathlib import PurePosixPath
from urllib.parse import urlparse

from django.core.files.base import ContentFile

from base.fields import is_image
from base.svg import UnsafeSvg, sanitize_svg

MAX_CREST_BYTES = 1024 * 1024

# football-data.org's clubColors is text like "Red / White" or "Claret / Sky Blue".
COLOURS = {
    "red": "#d71920",
    "blue": "#1b4fa0",
    "royal blue": "#1d4ed8",
    "navy blue": "#14254d",
    "navy": "#14254d",
    "dark blue": "#14254d",
    "sky blue": "#6cabdd",
    "light blue": "#6cabdd",
    "white": "#f5f5f5",
    "black": "#161616",
    "yellow": "#f6d000",
    "gold": "#c9a227",
    "green": "#16803c",
    "orange": "#f07d00",
    "claret": "#7a1f3d",
    "maroon": "#6d1b2c",
    "burgundy": "#6d1b2c",
    "purple": "#5b2a86",
    "violet": "#5b2a86",
    "grey": "#7a7f87",
    "gray": "#7a7f87",
    "silver": "#a9adb3",
    "amber": "#f2a900",
}
LIGHT = {"white", "yellow", "gold", "sky blue", "light blue", "silver", "amber"}
DARK_TEXT = "#111111"
LIGHT_TEXT = "#ffffff"


def badge_colours(club_colors):
    """(badge colour, initials colour) from the first colour named, or None if none is known."""
    for part in club_colors.lower().replace("-", "/").split("/"):
        name = part.strip()
        if name in COLOURS:
            return COLOURS[name], DARK_TEXT if name in LIGHT else LIGHT_TEXT
    return None


def crest_file(url, data):
    """A ContentFile ready for Team.crest, or None when the file is not a usable image.

    An SVG is sanitised (base.svg) before it is stored; any other file must be a real image.
    """
    if not data or len(data) > MAX_CREST_BYTES:
        return None
    name = PurePosixPath(urlparse(url).path).name or "crest"
    if name.lower().endswith(".svg") or data.lstrip()[:1] == b"<":
        try:
            clean = sanitize_svg(data)
        except UnsafeSvg:
            return None
        return ContentFile(clean, name=f"{PurePosixPath(name).stem}.svg")
    if not is_image(data[:12]):
        return None
    return ContentFile(data, name=name)
