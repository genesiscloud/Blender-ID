from django.apps import AppConfig


class BidMainConfig(AppConfig):
    name = 'bid_main'
    verbose_name = 'Blender-ID'

    def ready(self):
        # Import for side-effects.
        # noinspection PyUnresolvedReferences
        from . import signals, email
