from collections import OrderedDict
import pathlib

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.exceptions import ImproperlyConfigured


class MediaFinder(finders.FileSystemFinder):
    """
    A static files finder that uses the ``MEDIA_ROOT`` setting
    to locate files.

    Normally you would not use this, and have your web server
    serve those files.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Maps dir paths to an appropriate storage instance
        self.storages = OrderedDict()
        if not isinstance(settings.MEDIA_ROOT, (str, pathlib.Path)):
            raise ImproperlyConfigured("Your MEDIA_ROOT setting is not a str or pathlib.Path")

        # List of locations with static files
        self.locations = [('', str(settings.MEDIA_ROOT))]

        for prefix, root in self.locations:
            filesystem_storage = finders.FileSystemStorage(location=root)
            filesystem_storage.prefix = prefix
            self.storages[root] = filesystem_storage

    def find(self, path, all=False):
        return super().find(path, all=all)
