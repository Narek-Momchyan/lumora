from django.db import models

from base.constants import LANG_CHOICES
from base.fields import IMAGE_VALIDATORS


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
