from decimal import Decimal

from django.db import migrations

GAMES = [
    # slug, title, category, rtp, is_active, is_featured, sort_order
    ("neon-crash", "Neon Crash", "crash", "97.00", True, True, 10),
    ("zeus-legacy", "Zeus Legacy", "slot", "96.50", True, True, 20),
    ("lumora-roulette", "Lumora Roulette", "table", "97.30", True, True, 30),
    ("starlight-21", "Starlight 21", "table", "99.40", False, False, 40),
    ("volt-mines", "Volt Mines", "instant", "97.00", False, False, 50),
    ("pulse-plinko", "Pulse Plinko", "instant", "97.00", False, False, 60),
]


def add_games(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    for slug, title, category, rtp, is_active, is_featured, sort_order in GAMES:
        Game.objects.update_or_create(
            slug=slug,
            defaults={
                "title": title,
                "category": category,
                "rtp": Decimal(rtp),
                "is_active": is_active,
                "is_featured": is_featured,
                "sort_order": sort_order,
            },
        )


def remove_games(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    Game.objects.filter(slug__in=[game[0] for game in GAMES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("games", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_games, remove_games),
    ]
