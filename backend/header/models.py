from django.core.exceptions import ValidationError
from django.db import models

from base.constants import LANG_CHOICES
from base.fields import IMAGE_VALIDATORS
from games.models import Game


class Logo(models.Model):
    name = models.CharField(max_length=100)
    image = models.FileField(upload_to="images/header/", max_length=255, validators=IMAGE_VALIDATORS)

    class Meta:
        verbose_name_plural = "Logo"
        ordering = ["id"]

    def __str__(self):
        return self.name


class Language(models.Model):
    code = models.CharField(max_length=10, choices=LANG_CHOICES)
    name = models.CharField(max_length=50)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name_plural = "Languages"
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="unique_language_code"),
        ]

    def __str__(self):
        return self.name


class SidebarItem(models.Model):
    """A link of the sidebar, the site's only navigation.

    An item with a `category` opens the lobby filtered by it (`/?category=<code>`) and is the
    active one on the pages of that category's games.
    """

    lang = models.CharField(max_length=10, choices=LANG_CHOICES, db_index=True)
    title = models.CharField(max_length=100)
    url = models.CharField(max_length=255)
    category = models.CharField(
        max_length=16,
        choices=Game.Category.choices,
        blank=True,
        help_text="Set: the item filters the lobby, its url must be /?category=<code>",
    )
    order = models.PositiveSmallIntegerField(default=0)
    is_soon = models.BooleanField(default=False, help_text="On: shown disabled, with the soon label")

    class Meta:
        verbose_name_plural = "Sidebar items"
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["lang", "url"], name="unique_sidebar_item_lang_url"),
        ]

    def __str__(self):
        return f"{self.title} ({self.lang})"

    def clean(self):
        if self.category and self.url != category_url(self.category):
            raise ValidationError({"url": f"A category item opens {category_url(self.category)}."})


def category_url(code):
    return f"/?category={code}"


class HeaderLabel(models.Model):
    """Texts of the sidebar and the header in one language."""

    lang = models.CharField(max_length=10, choices=LANG_CHOICES, db_index=True)
    navigation_label = models.CharField(max_length=50)
    soon_label = models.CharField(max_length=30)
    search_placeholder = models.CharField(max_length=100)
    demo_badge = models.CharField(max_length=30)
    demo_note = models.CharField(max_length=255)
    balance_label = models.CharField(max_length=50)
    currency = models.CharField(max_length=10)
    menu_label = models.CharField(max_length=50)
    open_menu_label = models.CharField(max_length=50)
    close_menu_label = models.CharField(max_length=50)
    language_label = models.CharField(max_length=50)
    logout_button = models.CharField(max_length=50)
    server_unreachable = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = "Header labels"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["lang"], name="unique_header_label_lang"),
        ]

    def __str__(self):
        return f"Header labels ({self.lang})"
