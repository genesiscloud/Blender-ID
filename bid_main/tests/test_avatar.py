import pathlib
import shutil

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase


class AvatarModelTest(TestCase):
    def setUp(self) -> None:
        super().setUp()
        user_cls = get_user_model()
        self.user = user_cls(email='example@example.com',
                             full_name='Dr. Examplović')
        self.user.save()

        my_dir = pathlib.Path(__file__).absolute().parent
        self.fake_media_root = my_dir / 'media'

        self.settings_modifier = self.settings(
            MEDIA_ROOT=self.fake_media_root,
        )

        # Make sure the image cache is empty before we start testing.
        self.fake_media_cache = self.fake_media_root / 'cache'
        if self.fake_media_cache.exists():
            shutil.rmtree(self.fake_media_cache)

    def tearDown(self) -> None:
        if self.fake_media_cache.exists():
            shutil.rmtree(self.fake_media_cache)
        super().tearDown()

    def test_default_empty_avatar(self):
        self.assertFalse(self.user.avatar)
        self.assertEqual('', self.user.avatar.thumbnail_path())

        expect_url = f'https://example.com{settings.STATIC_URL}{settings.AVATAR_DEFAULT_FILENAME}'
        self.assertEqual(expect_url, self.user.avatar.thumbnail_url())

    def test_nonempty_avatar(self):
        avatar_fname = 'user-avatars/test-avatar.jpg'
        with self.settings_modifier:
            self.user.avatar = avatar_fname
            thumb_path = self.user.avatar.thumbnail_path()
            thumb_url = self.user.avatar.thumbnail_url()

        # Check the thumbnail cache
        all_found = list(self.fake_media_cache.glob('**/*.jpg'))
        self.assertEqual(1, len(all_found), 'Only one thumbnail should have been cached')

        # Check the thumbnail path
        rel_found = all_found[0].relative_to(self.fake_media_root)
        self.assertEqual(str(rel_found), thumb_path)

        # Check the thumbnail URL
        expect_url = f'https://example.com{settings.MEDIA_URL}{rel_found}'
        self.assertEqual(expect_url, thumb_url)
