from django.db import migrations

from slots.engine import JACKPOT_SEEDS


def add_pools(apps, schema_editor):
    JackpotPool = apps.get_model("wallet", "JackpotPool")
    for tier, seed in JACKPOT_SEEDS.items():
        JackpotPool.objects.get_or_create(tier=tier, defaults={"amount": seed})


def remove_pools(apps, schema_editor):
    apps.get_model("wallet", "JackpotPool").objects.filter(tier__in=JACKPOT_SEEDS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("slots", "0001_initial"),
        ("wallet", "0002_alter_transaction_kind_jackpotpool"),
    ]

    operations = [
        migrations.RunPython(add_pools, remove_pools),
    ]
