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
                          'roles': {}}, payload)

    def test_user_info_access_token_on_url(self):
        response = self.get(str(self.target_user.id), token_on_url=True)
        self.assertEqual(200, response.status_code, f'response: {response}')
        self.assertEqual('application/json', response.get('content-type'))

        payload = json.loads(response.content)
        self.assertEqual({'id': self.target_user.id,
                          'full_name': self.target_user.get_full_name(),
                          'email': self.target_user.email,
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
        create_user('target1@user.com', '123456', confirmed_email_at=timezone.now())
        create_user('target2@user.com', '123456', full_name='मूंगफली मक्खन प्रेमी')
        create_user('target3@user.com', '123456', confirmed_email_at=timezone.now())

        response = self.client.get(reverse('bid_api:stats'))
        self.assertEqual(200, response.status_code, f'response: {response}')
        self.assertEqual('application/json', response.get('content-type'))
        payload = json.loads(response.content)

        self.assertEqual({
            'users': {
                'unconfirmed': 2,
                'confirmed': 2,
                'total': 4,
            }
        }, payload)
