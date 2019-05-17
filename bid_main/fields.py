import urllib.parse

from django.conf import settings
from django.contrib.sites.models import Site
from django.db.models.fields.files import ImageFieldFile
import sorl.thumbnail


class AvatarFieldFile(ImageFieldFile):
    @staticmethod
    def _make_thumbnail_url(base: str, filename: str) -> str:
        site = Site.objects.get_current()
        abs_url = urllib.parse.urlunsplit(("https", site.domain, base, "", ""))
        thumb_url = urllib.parse.urljoin(abs_url, filename)
        return thumb_url

    @classmethod
    def default_thumbnail_url(cls) -> str:
        """Return the thumbnail URL used when the AvatarField is empty."""
        return cls._make_thumbnail_url(settings.STATIC_URL, settings.AVATAR_DEFAULT_FILENAME)

    def thumbnail_path(self) -> str:
        """Return the path of the thumbnailed avatar.

        The path is relative to MEDIA_ROOT.

        :return: the path to the thumbnail, or '' if the thumbnail is empty.
        """

        if not self:
            return ''

        size = settings.AVATAR_DEFAULT_SIZE_PIXELS
        geometry_string = f'{size}x{size}'
        thumb = sorl.thumbnail.get_thumbnail(
            self.name,
            geometry_string=geometry_string,
            crop="center")
        return thumb.name

    def thumbnail_url(self) -> str:
        """Return the absolute URL of the thumbnailed avatar.

        Returns either the URL of the cached thumbnail, or the URL
        of the default avatar (if this one is empty).
        """
        if not self:
            return self.default_thumbnail_url()
        return self._make_thumbnail_url(settings.MEDIA_URL, self.thumbnail_path())

    def __eq__(self, other) -> bool:
        if not isinstance(other, ImageFieldFile):
            return False

        if not self and not other:
            # Both are empty (but can have None or '' for name, so the equation below won't work).
            return True

        return self.name == other.name

    def __ne__(self, other) -> bool:
        return not self == other


class AvatarField(sorl.thumbnail.ImageField):
    """Sorl Thumbnail for user avatars."""
    attr_class = AvatarFieldFile
