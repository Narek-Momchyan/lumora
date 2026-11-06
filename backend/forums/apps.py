from django.apps import AppConfig
from django.db.models.signals import post_migrate

MODERATORS = "Forum moderators"
MODERATED = ["forum", "topic", "post", "postreport", "forumban", "bannedword", "forumlabel"]


def create_moderators(sender, **kwargs):
    """The staff group that moderates the forums and nothing else. Permissions exist only after a
    migration, so the group is made here, every time, idempotently."""
    from django.contrib.auth.models import Group, Permission

    group, _ = Group.objects.get_or_create(name=MODERATORS)
    permissions = Permission.objects.filter(content_type__app_label="forums", content_type__model__in=MODERATED)
    group.permissions.set(permissions)


class ForumsConfig(AppConfig):
    name = "forums"

    def ready(self):
        post_migrate.connect(create_moderators, sender=self)
