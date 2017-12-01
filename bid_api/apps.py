from django.apps import AppConfig


class BidAPIConfig(AppConfig):
    name = 'bid_api'
    verbose_name = 'Blender-ID API'

    def ready(self):
        # noinspection PyUnresolvedReferences
        from . import signals
