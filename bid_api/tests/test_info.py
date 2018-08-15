from datetime import timedelta
import json

from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.utils import timezone

from .abstract import AbstractAPITest, AccessToken, UserModel
from bid_main.models import Role


class UserInfoTest(AbstractAPITest):
    access_token_scope = 'userinfo'

    def setUp(self):
        self.target_user = UserModel.objects.create_user(
            'target@user.com', '123456',
            full_name='मूंगफली मक्खन प्रेमी',
            nickname='मूँगफली',
        )

    def get(self, user_id: str, *, access_token='', token_on_url=False) -> HttpResponse:
        url_path = reverse('bid_api:user-info-by-id', kwargs={'user_id': user_id})
        response = self.authed_get(url_path, access_token=access_token, token_on_url=token_on_url)
        return response

    def test_user_info_happy(self):
        response = self.get(str(self.target_user.id))
        self.assertEqual(200, response.status_code, f'response: {response}')
        self.assertEqual('application/json', response.get('content-type'))

        payload = json.loads(response.content)
        self.assertEqual({'id': self.target_user.id,
                          'full_name': self.target_user.get_full_name(),
                          'email': self.target_user.email,
                          'nickname': self.target_user.nickname,
                          'roles': {}}, payload)

    def test_user_info_access_token_on_url(self):
        response = self.get(str(self.target_user.id), token_on_url=True)
        self.assertEqual(200, response.status_code, f'response: {response}')
        self.assertEqual('application/json', response.get('content-type'))

        payload = json.loads(response.content)
        self.assertEqual({'id': self.target_user.id,
                          'full_name': self.target_user.get_full_name(),
                          'email': self.target_user.email,
                          'nickname': self.target_user.nickname,
                          'roles': {}}, payload)

    def test_user_info_not_found(self):
        response = self.get('650904')
        self.assertEqual(404, response.status_code, f'response: {response}')

    def test_user_info_bad_id(self):
        url_path = reverse('bid_api:user-info-by-id', kwargs={'user_id': '4444444'})
        url_path = url_path.replace('4444444', 'jemoeder')
        response = self.authed_get(url_path)
        self.assertEqual(404, response.status_code, f'response: {response}')

    def test_user_info_with_roles(self):
        # Give the user a role
        role = Role(name='cloud_admin')
        role.save()
        self.target_user.roles.add(role)
        self.target_user.save()

        response = self.get(str(self.target_user.id))
        self.assertEqual(200, response.status_code, f'response: {response}')
        self.assertEqual('application/json', response.get('content-type'))

        payload = json.loads(response.content)
        self.assertEqual({'id': self.target_user.id,
                          'full_name': self.target_user.get_full_name(),
                          'email': self.target_user.email,
                          'nickname': self.target_user.nickname,
                          'roles': {'cloud_admin': True}}, payload)

    def test_bad_token_scope(self):
        wrong_token = AccessToken.objects.create(
            user=self.user,
            scope='email',
            expires=timezone.now() + timedelta(seconds=300),
            token='token-with-wrong-scope',
            application=self.application
        )
        wrong_token.save()
        response = self.get(self.target_user.id, access_token=wrong_token.token)
        self.assertEqual(403, response.status_code)

    def test_own_user_info(self):
        normal_token = AccessToken.objects.create(
            user=self.target_user,
            scope='email',
            expires=timezone.now() + timedelta(seconds=300),
            token='token-with-wrong-scope',
            application=self.application
        )
        normal_token.save()

        def assert_payload_ok(response):
            self.assertEqual(200, response.status_code)
            payload = json.loads(response.content)
            self.assertEqual({'id': self.target_user.id,
                              'full_name': self.target_user.get_full_name(),
                              'email': self.target_user.email,
                              'nickname': self.target_user.nickname,
                              'roles': {}}, payload)

        url_path = reverse('bid_api:user')
        resp = self.authed_get(url_path, access_token=normal_token.token)
        assert_payload_ok(resp)

        # Enable this code once https://github.com/evonove/django-oauth-toolkit/issues/547 is fixed.
        # resp = self.authed_get(url_path, access_token=normal_token.token, token_on_url=True)
        # assert_payload_ok(resp)

    def test_own_user_info_anonymous(self):
        response = self.client.get(reverse('bid_api:user'))
        self.assertEqual(403, response.status_code)


class UserStatsTest(AbstractAPITest):

    def test_stats(self):
        create_user = UserModel.objects.create_user
        create_user('target1@user.com', '123456', confirmed_email_at=timezone.now(), nickname='1')
        create_user('target2@user.com', '123456', full_name='मूंगफली मक्खन प्रेमी', nickname='2',
                    privacy_policy_agreed=timezone.now())
        create_user('target3@user.com', '123456', confirmed_email_at=timezone.now(), nickname='3')

        response = self.client.get(reverse('bid_api:stats'))
        self.assertEqual(200, response.status_code, f'response: {response}')
        self.assertEqual('application/json', response.get('content-type'))
        payload = json.loads(response.content)

        self.assertEqual({
            'users': {
                'unconfirmed': 2,
                'confirmed': 2,
                'total': 4,
                'privacy_policy_agreed': {'latest': 1, 'never': 3, 'obsolete': 0},
            }
        }, payload)


class UserBadgeTest(AbstractAPITest):
    access_token_scope = 'badge'

    def setUp(self):
        self.target_user = UserModel.objects.create_user(
            'target@user.com', '123456',
            full_name='मूंगफली मक्खन प्रेमी',
            nickname='मूँगफली',
        )

        # Grant a couple of roles.
        self.badge_cloud = Role(name='⛅cloud_subscriber',
                                is_badge=True,
                                is_active=True,
                                is_public=True,
                                label='⛅ Subscriber',
                                description='¡Awesome T-Rex!',
                                link='https://cloud.blender.org/',
                                badge_img='badges/t-rex.png',
                                badge_img_width=120,
                                badge_img_height=100)
        self.badge_cloud.save()

        self.badge_nonpublic = Role(name='nonpublic❌',
                                    is_badge=True,
                                    is_active=True,
                                    is_public=False,
                                    label='❌ NONPUB ❌')
        self.badge_nonpublic.save()

        self.role_public = Role(name='janitor',
                                is_badge=False,
                                is_active=True,
                                is_public=True,
                                label='the poodle')
        self.role_public.save()

        self.target_user.roles.add(self.badge_cloud)
        self.target_user.roles.add(self.badge_nonpublic)
        self.target_user.roles.add(self.role_public)
        self.target_user.save()

    def get(self, user_id: str, *, access_token='', token_on_url=False) -> HttpResponse:
        url_path = reverse('bid_api:user-badges-by-id', kwargs={'user_id': user_id})
        response = self.authed_get(url_path, access_token=access_token, token_on_url=token_on_url)
        return response

    def test_other_user(self):
        response = self.get(str(self.target_user.id))
        self.assertEqual(403, response.status_code, f'response: {response}')

    def test_happy(self):
        target_user_token = AccessToken.objects.create(
            user=self.target_user,
            scope='email badge',
            expires=timezone.now() + timedelta(seconds=300),
            token='token-with-badge-scope',
            application=self.application
        )
        target_user_token.save()

        def get():
            return self.get(str(self.target_user.id), access_token=target_user_token.token)

        response = get()
        self.assertEqual(200, response.status_code, f'response: {response}')
        self.assertEqual('application/json', response.get('content-type'))
        payload = json.loads(response.content)
        self.assertEqual({'user_id': self.target_user.id,
                          'badges': {
                              '⛅cloud_subscriber': {
                                  'label': '⛅ Subscriber',
                                  'description': '¡Awesome T-Rex!',
                                  'link': 'https://cloud.blender.org/',
                                  'image': 'http://example.com/media/badges/t-rex.png',
                                  'image_width': 120,
                                  'image_height': 100,
                              }
                          }}, payload)

        # Make the Poodle a badge
        self.role_public.is_badge = True
        self.role_public.save()

        response = get()
        payload = json.loads(response.content)
        self.assertEqual({'user_id': self.target_user.id,
                          'badges': {
                              '⛅cloud_subscriber': {
                                  'label': '⛅ Subscriber',
                                  'description': '¡Awesome T-Rex!',
                                  'link': 'https://cloud.blender.org/',
                                  'image': 'http://example.com/media/badges/t-rex.png',
                                  'image_width': 120,
                                  'image_height': 100,
                              },
                              'janitor': {
                                  'label': 'the poodle',
                              },
                          }}, payload)

    def test_bad_token_scope(self):
        wrong_token = AccessToken.objects.create(
            user=self.user,
            scope='email',
            expires=timezone.now() + timedelta(seconds=300),
            token='token-with-wrong-scope',
            application=self.application
        )
        wrong_token.save()
        response = self.get(self.target_user.id, access_token=wrong_token.token)
        self.assertEqual(403, response.status_code)

    def test_own_badge_bad_token_scope(self):
        wrong_token = AccessToken.objects.create(
            user=self.target_user,
            scope='email',
            expires=timezone.now() + timedelta(seconds=300),
            token='token-with-wrong-scope',
            application=self.application
        )
        wrong_token.save()
        response = self.get(self.target_user.id, access_token=wrong_token.token)
        self.assertEqual(403, response.status_code)

    def test_nonexisting_user(self):
        response = self.get(str(self.target_user.id + 1))
        # Nonexisting user means that you're requesting for another user,
        # which results in a 403 Forbidden.
        self.assertEqual(403, response.status_code, f'response: {response}')
