from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models

from base.constants import LANG_CHOICES


class PlayerManager(UserManager):
    def get_by_natural_key(self, username):
        # Log in with any letter case: Narek@Mail.com == narek@mail.com
        return self.get(email__iexact=username)


class User(AbstractUser):
    """Lumora player. Logs in with email; username is kept equal to the email."""

    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=40, blank=True)

    objects = PlayerManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.display_name or self.email


class LoginPageLabel(models.Model):
    """Every text of the login page in one language."""

    lang = models.CharField(max_length=10, choices=LANG_CHOICES, db_index=True)
    hero_title_line_1 = models.CharField(max_length=100)
    hero_title_line_2 = models.CharField(max_length=100)
    hero_text = models.CharField(max_length=255)
    stat_games = models.CharField(max_length=50)
    stat_rtp = models.CharField(max_length=50)
    stat_real_money = models.CharField(max_length=50)
    footer_note = models.CharField(max_length=255)
    tab_login = models.CharField(max_length=50)
    tab_signup = models.CharField(max_length=50)
    login_title = models.CharField(max_length=100)
    login_subtitle = models.CharField(max_length=255)
    signup_title = models.CharField(max_length=100)
    signup_subtitle = models.CharField(max_length=255)
    email_label = models.CharField(max_length=50)
    email_placeholder = models.CharField(max_length=100)
    password_label = models.CharField(max_length=50)
    display_name_label = models.CharField(max_length=100)
    login_button = models.CharField(max_length=50)
    login_pending = models.CharField(max_length=50)
    signup_button = models.CharField(max_length=50)
    signup_pending = models.CharField(max_length=50)
    or_text = models.CharField(max_length=20)
    create_account_button = models.CharField(max_length=100)
    have_account_button = models.CharField(max_length=100)
    server_unreachable = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = "Login page labels"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["lang"], name="unique_login_page_label_lang"),
        ]

    def __str__(self):
        return f"Login page labels ({self.lang})"
