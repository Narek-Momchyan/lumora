from django.db import migrations, models

SHORT = 50
ICON = 10

FIELDS = [
    ("bonus_blessing", 100),
    ("bonus_begin", SHORT),
    ("bonus_complete", 100),
    ("tap_to_continue", SHORT),
    ("jackpot_icon_mini", ICON),
    ("jackpot_icon_minor", ICON),
    ("jackpot_icon_major", ICON),
    ("jackpot_icon_grand", ICON),
]


def add_field(name, max_length):
    return migrations.AddField(
        model_name="zeuspagelabel",
        name=name,
        field=models.CharField(default="", max_length=max_length),
        preserve_default=False,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("slots", "0003_zeus_page_label_controls"),
    ]

    operations = [add_field(*field) for field in FIELDS]
