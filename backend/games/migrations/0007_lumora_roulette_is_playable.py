from django.db import migrations


def open_game(apps, schema_editor):
    apps.get_model("games", "Game").objects.filter(slug="lumora-roulette").update(is_playable=True)


def close_game(apps, schema_editor):
    apps.get_model("games", "Game").objects.filter(slug="lumora-roulette").update(is_playable=False)


class Migration(migrations.Migration):
    dependencies = [
        ("games", "0006_zeus_legacy_is_playable"),
    ]

    operations = [
        migrations.RunPython(open_game, close_game),
    ]
