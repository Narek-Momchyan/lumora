import json
from pathlib import Path

from django.conf import settings
from django.core.management.color import no_style
from django.db import connection, models

from accounts.models import LoginPageLabel
from crash.models import CrashPageLabel
from errors.models import ErrorMessage
from games.models import GameCategory, LobbyPageLabel
from header.models import HeaderLabel, Language, Logo, SidebarItem
from roulette.models import RoulettePageLabel
from slots.models import SlotSymbol, SlotSymbolName, ZeusPageLabel
from sports.models import SportsPageLabel
from .language import LANG_CODES

SAMPLE_DB = Path(settings.BASE_DIR) / "base" / "sample_db.json"
LANGS = LANG_CODES

COLLECTIONS = {
    "logos": Logo,
    "languages": Language,
    "header_labels": HeaderLabel,
    "sidebar_items": SidebarItem,
    "login_page_labels": LoginPageLabel,
    "game_categories": GameCategory,
    "lobby_page_labels": LobbyPageLabel,
    "slot_symbols": SlotSymbol,
    "slot_symbol_names": SlotSymbolName,
    "zeus_page_labels": ZeusPageLabel,
    "crash_page_labels": CrashPageLabel,
    "roulette_page_labels": RoulettePageLabel,
    "sports_page_labels": SportsPageLabel,
    "error_messages": ErrorMessage,
}


def to_file_names(model, values):
    """FileFields store paths relative to MEDIA_ROOT: "/media/images/x.png" -> "images/x.png".

    A foreign key comes as the value it points to, so it goes in through its column: symbol_id.
    """
    for field in model._meta.concrete_fields:
        value = values.get(field.name)
        if isinstance(field, models.FileField) and isinstance(value, str) and value.startswith(settings.MEDIA_URL):
            values[field.name] = value[len(settings.MEDIA_URL) :]
        elif field.is_relation and field.name in values:
            values[field.attname] = values.pop(field.name)
    return values


def load_sample(data):
    """Fill the content tables from the sample structure. Expects empty tables."""
    for name, model in COLLECTIONS.items():
        rows = data[name]
        if isinstance(rows, dict):
            rows = [rows]
        for row in rows:
            model.objects.create(**to_file_names(model, dict(row)))


def clear_sample():
    for model in COLLECTIONS.values():
        model.objects.all().delete()


def reset_sequences():
    statements = connection.ops.sequence_reset_sql(no_style(), list(COLLECTIONS.values()))
    with connection.cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)


def read_sample(path=SAMPLE_DB):
    return json.loads(Path(path).read_text(encoding="utf-8"))
