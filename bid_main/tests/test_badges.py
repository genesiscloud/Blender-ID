import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

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


class BadgeTogglePrivateTest(TestCase):
    def test_toggle(self):
        badge_normal = models.Role.objects.create(
            id=100, is_badge=True, is_public=True, is_active=True,
            name='normal', badge_img='badges/badge_cloud.png')

        user_cls = get_user_model()
        user = user_cls(email='example@example.com', full_name='Dr. Examplović')
        user.save()

        user.roles.add(badge_normal)
        user.save()

        self.assertEqual([badge_normal.pk], [badge.pk for badge in user.public_badges()])

        self.client.force_login(user)

        # Toggle private
        resp = self.client.post(reverse('bid_main:badge_toggle_private'),
                                data={'badge_name': 'normal'})
        self.assertEqual(200, resp.status_code)
        self.assertEqual({'is_private': True}, json.loads(resp.content))
        self.assertEqual([], [badge.pk for badge in user.public_badges()])

        # Toggle public
        resp = self.client.post(reverse('bid_main:badge_toggle_private'),
                                data={'badge_name': 'normal'})
        self.assertEqual(200, resp.status_code)
        self.assertEqual({'is_private': False}, json.loads(resp.content))
        self.assertEqual([badge_normal.pk], [badge.pk for badge in user.public_badges()])
