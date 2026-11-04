from django.db import models

from base.constants import LANG_CHOICES


class SportsPageLabel(models.Model):
    """Every text of the football home page in one language.

    Until the football data arrives (phase S1), the page shows only this hero.
    """

    lang = models.CharField(max_length=10, choices=LANG_CHOICES, db_index=True)
    page_title = models.CharField(max_length=100)
    page_description = models.CharField(max_length=255)
    hero_eyebrow = models.CharField(max_length=100)
    hero_title = models.CharField(max_length=150)
    hero_text = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = "Sports page labels"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["lang"], name="unique_sports_page_label_lang"),
        ]

    def __str__(self):
        return f"Sports page labels ({self.lang})"
