from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from oauth2_provider.models import get_access_token_model, get_refresh_token_model

AccessToken = get_access_token_model()
RefreshToken = get_refresh_token_model()
User = get_user_model()


# We don't import django.contrib.auth.models.User directly. Instead, we use
# django.contrib.auth.get_user_model() as described at:
# https://docs.djangoproject.com/en/1.9/topics/auth/customizing/

class BlenderIdAddonSupportTest(TestCase):
    fixtures = ['bid_addon_support/fixtures/bid_addon_support']

    def setUp(self):
        self._create_user()

    def test_verify_identity_happy(self,
                                   email='sybren@example.com',
                                   password='jemoeder'):
        """
        Happy flow of the Blender ID add-on authentication.
        """

        url = reverse('addon_support:identify')
        resp = self.client.post(url, {
            'email': email,
            'password': password,
            'host_label': 'unittest',
        })
        self.assertEqual(200, resp.status_code)

        data = resp.json()
        self.assertEqual('success', data['status'])
        token_data = data['data']['oauth_token']

        # There must be a token with the given information
        dbtoken = AccessToken.objects.get(token=token_data['access_token'])
        self.assertIsNotNone(dbtoken)

        return dbtoken

    def test_verify_identity_happy_username(self):
        """
        Happy flow of the Blender ID add-on authentication using 'username' form field.
        """

        url = reverse('addon_support:identify')
        resp = self.client.post(url, {
            'username': 'sybren@example.com',
            'password': 'jemoeder',
            'host_label': 'unittest',
        })
        self.assertEqual(200, resp.status_code)

        data = resp.json()
        self.assertEqual('success', data['status'])

    def test_verify_identity_bad_password(self):
        """
        Bad password given
        """

        url = reverse('addon_support:identify')
        resp = self.client.post(url, {
            'email': 'sybren@stuvel.eu',
            'password': 'bad password ẅïẗḧ üñïčöđë',
            'host_label': 'unittest',
        })
        self.assertEqual(200, resp.status_code)

        data = resp.json()
        self.assertEqual('fail', data['status'])
        self.assert_no_tokens()

    def _create_user(self,
                     email='sybren@example.com',
                     password='jemoeder',
                     full_name='Sybren Stüvel',
                     nickname='dr.Sybren') -> User:
        user = User.objects.create_user(email=email,
                                        password=password,
                                        full_name=full_name,
                                        nickname=nickname)
        user.save()
        return user

    def test_verify_identity_bad_username(self):
        """
        Bad password given
        """

        url = reverse('addon_support:identify')
        resp = self.client.post(url, {
            'username': 'othername',
            'password': 'jemoeder',
            'host_label': 'unittest',
        })
        self.assertEqual(200, resp.status_code)

        data = resp.json()
        self.assertEqual('fail', data['status'])
        self.assert_no_tokens()

    def assert_no_tokens(self):
        self.assertEqual([], list(AccessToken.objects.all()))
        self.assertEqual([], list(RefreshToken.objects.all()))

    def test_delete_token(self):
        # First make sure there is a token.
        dbtoken = self.test_verify_identity_happy()

        url = reverse('addon_support:delete_token')
        resp = self.client.post(url, {
            'user_id': dbtoken.user.id,
            'token': dbtoken.token,
        })
        self.assertEqual(200, resp.status_code)
        self.assert_no_tokens()

    def test_delete_token_invalid_form(self):
        dbtoken = self.test_verify_identity_happy()

        url = reverse('addon_support:delete_token')
        resp = self.client.post(url, {
            'user_id': 'garçon',
            'token': dbtoken.token,
        })
        self.assertEqual(400, resp.status_code)
        self.assertEqual(1, AccessToken.objects.count())

    def test_delete_other_token(self):
        # First make sure there is a token, but owned by someone else.
        self._create_user(email='other@user.nl', nickname='dr.Other')
        other_token = self.test_verify_identity_happy(email='other@user.nl')
        my_token = self.test_verify_identity_happy()

        url = reverse('addon_support:delete_token')
        resp = self.client.post(url, {
            'user_id': my_token.user.id,
            'token': other_token.token,
        })
        self.assertEqual(403, resp.status_code)
        self.assertEqual(sorted([my_token.token, other_token.token]),
                          sorted(t.token for t in AccessToken.objects.all()))

    def test_validate_token_happy(self):
        # First make sure there is a token.
        dbtoken = self.test_verify_identity_happy()

        url = reverse('addon_support:validate_token')
        resp = self.client.post(url, {
            'token': dbtoken.token,
        })
        self.assertEqual(200, resp.status_code)

        data = resp.json()
        self.assertEqual('success', data['status'])
        self.assertEqual(dbtoken.user.id, data['user']['id'])
        self.assertEqual('sybren@example.com', data['user']['email'])
        self.assertEqual('Sybren Stüvel', data['user']['full_name'])

    def test_create_subclient_token(self):
        dbtoken = self.test_verify_identity_happy()

        url = reverse('addon_support:subclient_create_token')
        resp = self.client.post(url, {
            'subclient_id': 'PILLAR',
            'host_label': 'unit testing stuff',
        }, HTTP_AUTHORIZATION=f'Bearer {dbtoken.token}')
        self.assertEqual(201, resp.status_code)
