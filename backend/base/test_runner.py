from django.test import override_settings
from django.test.runner import DiscoverRunner

IN_MEMORY_CHANNEL_LAYER = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


class SkipSlowTestsRunner(DiscoverRunner):
    """`manage.py test` skips tests tagged "slow". `manage.py test --tag slow` runs only them.

    Tests never need Redis: the channel layer stays in memory.
    """

    def __init__(self, *args, tags=None, exclude_tags=None, **kwargs):
        exclude_tags = set(exclude_tags or [])
        if not tags:
            exclude_tags.add("slow")
        super().__init__(*args, tags=tags, exclude_tags=exclude_tags, **kwargs)

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self.channel_layers = override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYER)
        self.channel_layers.enable()

    def teardown_test_environment(self, **kwargs):
        self.channel_layers.disable()
        super().teardown_test_environment(**kwargs)
