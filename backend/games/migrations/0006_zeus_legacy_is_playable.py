from django.db import migrations


def open_game(apps, schema_editor):
    apps.get_model("games", "Game").objects.filter(slug="zeus-legacy").update(is_playable=True)


def close_game(apps, schema_editor):
    apps.get_model("games", "Game").objects.filter(slug="zeus-legacy").update(is_playable=False)


class Migration(migrations.Migration):
    dependencies = [
        ("games", "0005_zeus_legacy_rules"),
    ]

    operations = [
        migrations.RunPython(open_game, close_game),
    ]
