from django.test.runner import DiscoverRunner


class SkipSlowTestsRunner(DiscoverRunner):
    """`manage.py test` skips tests tagged "slow". `manage.py test --tag slow` runs only them."""

    def __init__(self, *args, tags=None, exclude_tags=None, **kwargs):
        exclude_tags = set(exclude_tags or [])
        if not tags:
            exclude_tags.add("slow")
        super().__init__(*args, tags=tags, exclude_tags=exclude_tags, **kwargs)
