from django.db import migrations

# A starter list only: real-money and ad words, and a few mild insults. The moderators extend it in the admin.
# It is not in load_sample on purpose: a public list of banned words would teach people how to get around it,
# and `load_sample --reset` must never wipe what the moderators added.
WORDS = [
    ("en", "1xbet", False), ("en", "bet365", False), ("en", "betway", False), ("en", "promo code", False),
    ("en", "real money", False), ("en", "idiot", False), ("en", "moron", False), ("en", "scum", False),
    ("ru", "1хбет", False), ("ru", "промокод", True), ("ru", "реальные деньги", False), ("ru", "идиот", True),
    ("ru", "дебил", True), ("ru", "мразь", True),
    ("am", "պրոմոկոդ", True), ("am", "իրական փող", False), ("am", "ապուշ", True), ("am", "տականք", True),
]


def add_words(apps, schema_editor):
    from forums.text import key_of  # the same folding the matcher uses

    BannedWord = apps.get_model("forums", "BannedWord")
    for lang, word, inside in WORDS:
        BannedWord.objects.get_or_create(lang=lang, key=key_of(word), defaults={"word": word, "inside_words": inside})


class Migration(migrations.Migration):
    dependencies = [("forums", "0001_initial")]
    operations = [migrations.RunPython(add_words, migrations.RunPython.noop)]
