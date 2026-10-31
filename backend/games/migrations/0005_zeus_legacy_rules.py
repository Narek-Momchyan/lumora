from decimal import Decimal

from django.db import migrations

BEFORE = {"rtp": Decimal("96.50"), "min_bet": Decimal("1.00"), "max_bet": Decimal("10000.00"), "image": ""}
# 96.60 is the game RTP measured over 5,000,000 rounds (95.85) plus the jackpots (0.74).
# The bet limits keep every jackpot chance well under 100%, even for a bonus buy.
AFTER = {
    "rtp": Decimal("96.60"),
    "min_bet": Decimal("0.20"),
    "max_bet": Decimal("100.00"),
    "image": "images/zeus/zeus.png",
}


def apply_rules(apps, schema_editor):
    apps.get_model("games", "Game").objects.filter(slug="zeus-legacy").update(**AFTER)


def undo_rules(apps, schema_editor):
    apps.get_model("games", "Game").objects.filter(slug="zeus-legacy").update(**BEFORE)


class Migration(migrations.Migration):
    dependencies = [
        ("games", "0004_neon_crash_is_playable"),
    ]

    operations = [
        migrations.RunPython(apply_rules, undo_rules),
    ]
