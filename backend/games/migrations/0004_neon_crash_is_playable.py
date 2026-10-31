from django.db import migrations

PLAYABLE_GAMES = ["neon-crash"]


def set_playable(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    Game.objects.filter(slug__in=PLAYABLE_GAMES).update(is_playable=True)


def unset_playable(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    Game.objects.filter(slug__in=PLAYABLE_GAMES).update(is_playable=False)


class Migration(migrations.Migration):
    dependencies = [
        ("games", "0003_game_image_game_is_playable_gamecategory_and_more"),
    ]

    operations = [
        migrations.RunPython(set_playable, unset_playable),
    ]
