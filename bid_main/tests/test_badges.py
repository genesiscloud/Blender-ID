from django.test import TestCase

from .. import models


class BadgeTest(TestCase):
    def test_badge_without_image(self):
        badge_normal = models.Role.objects.create(
            id=100, is_badge=True, is_public=True, is_active=True,
            badge_img='badges/badge_cloud.png')
        badge_noimg = models.Role.objects.create(
            id=101, is_badge=True, is_public=True, is_active=True,
            badge_img='')
        badge_private = models.Role.objects.create(
            id=102, is_badge=True, is_public=False, is_active=True,
            badge_img='badges/badge_cloud.png')
        badge_inactive = models.Role.objects.create(
            id=103, is_badge=True, is_public=True, is_active=False,
            badge_img='badges/badge_cloud.png')
        nobadge = models.Role.objects.create(
            id=104, is_badge=False, is_public=True, is_active=False,
            badge_img='badges/badge_cloud.png')

        badge_pks = set(role.pk for role in models.Role.objects.badges())
        self.assertEqual({badge_normal.pk}, badge_pks)
