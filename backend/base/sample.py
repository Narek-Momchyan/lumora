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


# What makes a row "the same row" when load_sample only adds what is missing. The logo has no key:
# the site has one, so an existing logo counts as present.
NATURAL_KEYS = {
    "logos": [],
    "languages": ["code"],
    "header_labels": ["lang"],
    "sidebar_items": ["lang", "mode", "url"],
    "login_page_labels": ["lang"],
    "game_categories": ["lang", "code"],
    "lobby_page_labels": ["lang"],
    "slot_symbols": ["code"],
    "slot_symbol_names": ["lang", "symbol"],
    "zeus_page_labels": ["lang"],
    "crash_page_labels": ["lang"],
    "roulette_page_labels": ["lang"],
    "sports_page_labels": ["lang"],
    "error_messages": ["lang", "code"],
}


def rows_of(data, name):
    rows = data[name]
    return [rows] if isinstance(rows, dict) else rows


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
    """Fill the content tables from the sample structure, ids included. Expects empty tables."""
    for name, model in COLLECTIONS.items():
        for row in rows_of(data, name):
            model.objects.create(**to_file_names(model, dict(row)))


def add_missing(data):
    """Add only the sample rows that are missing; rows edited in the admin stay as they are.

    The database picks the ids, so a new row never collides with one added in the admin.
    Returns the number of added rows.
    """
    added = 0
    for name, model in COLLECTIONS.items():
        for row in rows_of(data, name):
            values = to_file_names(model, {key: value for key, value in row.items() if key != "id"})
            key = {}
            for field in NATURAL_KEYS[name]:
                column = model._meta.get_field(field).attname
                key[column] = values[column]
            if model.objects.filter(**key).exists():
                continue
            model.objects.create(**values)
            added += 1
    return added


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
