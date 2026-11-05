from django.db import migrations

# Our six leagues (design/sports-spec.md). The sync fills provider ids, seasons, teams and matches.
COMPETITIONS = [
    ("PL", "Premier League", "images/sidebar/flag-england.png"),
    ("PD", "Primera Division", "images/sidebar/flag-spain.png"),
    ("SA", "Serie A", "images/sidebar/flag-italy.png"),
    ("BL1", "Bundesliga", "images/sidebar/flag-germany.png"),
    ("FL1", "Ligue 1", "images/sidebar/flag-france.png"),
    ("CL", "UEFA Champions League", "images/sidebar/champions-league.png"),
]


def seed(apps, schema_editor):
    Competition = apps.get_model("sports", "Competition")
    for order, (code, name, flag) in enumerate(COMPETITIONS, 1):
        Competition.objects.get_or_create(code=code, defaults={"name": name, "flag": flag, "order": order})


class Migration(migrations.Migration):
    dependencies = [
        ("sports", "0002_football_data"),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
