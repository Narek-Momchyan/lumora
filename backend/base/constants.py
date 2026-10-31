from datetime import timedelta
from decimal import Decimal

# Lumora coins (LC) are demo money: no cash value, never bought or withdrawn.
CURRENCY = "LC"
SIGNUP_BONUS = Decimal("10000.00")
DAILY_BONUS = Decimal("5000.00")
DAILY_BONUS_COOLDOWN = timedelta(hours=24)

# `am` is our code for Armenian; the HTML lang attribute is `hy`.
LANG_CHOICES = [
    ("en", "English"),
    ("am", "Հայերեն"),
    ("ru", "Русский"),
]
DEFAULT_LANG = "en"
