from django.db import migrations, models

SHORT = 50

FIELDS = [
    ("free_spins_won", 100, "{count} is replaced with the number"),
    ("buy_bonus_title", 100, None),
    ("buy_bonus_text", 255, "{amount} is replaced with the price"),
    ("buy_bonus_confirm", SHORT, None),
    ("cancel", SHORT, None),
    ("stop", SHORT, None),
    ("skip", SHORT, None),
    ("auto_spins_left", SHORT, "{count} is replaced with the number"),
    ("auto_menu_label", 100, None),
    ("mute", SHORT, None),
    ("unmute", SHORT, None),
    ("bet_lower", SHORT, None),
    ("bet_raise", SHORT, None),
    ("jackpots_label", SHORT, None),
    ("history_title", 100, None),
    ("history_empty", 255, None),
    ("history_time", SHORT, None),
    ("history_cost", SHORT, None),
    ("history_win", SHORT, None),
    ("history_bonus_buy", SHORT, None),
    ("history_free_spins", SHORT, None),
    ("history_seed_hash", SHORT, None),
    ("history_client_seed", SHORT, None),
    ("history_nonce", SHORT, None),
]


def add_field(name, max_length, help_text):
    extra = {"help_text": help_text} if help_text else {}
    return migrations.AddField(
        model_name="zeuspagelabel",
        name=name,
        field=models.CharField(default="", max_length=max_length, **extra),
        preserve_default=False,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("slots", "0002_seed_jackpot_pools"),
    ]

    operations = [add_field(*field) for field in FIELDS]
