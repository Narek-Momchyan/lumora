from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


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
