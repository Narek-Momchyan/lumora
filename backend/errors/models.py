from django.db import models

from base.constants import LANG_CHOICES


class ErrorMessage(models.Model):
    """The text of an API error in one language. Text may use {placeholders}, like {min}."""

    code = models.CharField(max_length=50, db_index=True)
    lang = models.CharField(max_length=10, choices=LANG_CHOICES, db_index=True)
    text = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = "Error messages"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["code", "lang"], name="unique_error_message_code_lang"),
        ]

    def __str__(self):
        return f"{self.code} ({self.lang})"
