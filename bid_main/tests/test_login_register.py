from urllib.parse import urlencode

from django.urls import reverse, reverse_lazy
from django.contrib.auth import get_user_model
from django.test import TestCase

import oauth2_provider.models as oa2_models

Application = oa2_models.get_application_model()
AccessToken = oa2_models.get_access_token_model()
UserModel = get_user_model()


class RegisterTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = UserModel.objects.create_user('test@user.com', '123456')

    def test_register_happy(self):
        response = self.client.post(
            reverse('bid_main:register'),
            {
                'full_name': 'Šuper Ũseŕ',
                'email': 'super@hero.com',
                'nickname': 'Apenút',
            })
        self.assertEqual(302, response.status_code, f'response: {response}')
        redirect_url = reverse('bid_main:register-done')
        self.assertEqual(redirect_url, response['location'])

        # Check the user's info
        db_user = UserModel.objects.get(email='super@hero.com')
        self.assertEqual('Šuper Ũseŕ', db_user.full_name)
        self.assertEqual(2, len(UserModel.objects.all()))

    def test_user_already_exists(self):
        response = self.client.post(
            reverse('bid_main:register'),
            {
                'full_name': 'Šuper Ũseŕ',
                'email': self.user.email,
                'nickname': 'Apenút',
            })
        # This should render a template just fine; it shouldn't cause an internal error.
        self.assertEqual(200, response.status_code, f'respose: {response}')
        self.assertEqual(1, len(UserModel.objects.all()))


class TestLogout(TestCase):
    logout_url = reverse_lazy('bid_main:logout')

    def setUp(self):
        super().setUp()
        self.user = UserModel.objects.create_user('test@user.com', '123456')
        self.client.force_login(self.user)

    def assertDefaultRedirect(self, resp):
        self.assertEqual(302, resp.status_code)
        self.assertEqual(reverse('bid_main:about'), resp['Location'])

    def test_no_next_no_referer(self):
        resp = self.client.get(self.logout_url)
        self.assertDefaultRedirect(resp)

    def test_next_no_referer(self):
        resp = self.client.get(f'{self.logout_url}?next=https://www.blender.org/')
        self.assertDefaultRedirect(resp)

    def test_next_mismatched_referer(self):
        resp = self.client.get(f'{self.logout_url}?next=https://www.blender.org/',
                               REFERER='https://exploding-kittens.com/')
        self.assertDefaultRedirect(resp)

    def test_next_downgrade_security(self):
        resp = self.client.get(
            f'{self.logout_url}?next=http://exploding-kittens.com/logout-confirm',
            HTTP_REFERER='https://exploding-kittens.com/')
        self.assertDefaultRedirect(resp)

    def test_next_matching_referer(self):
        resp = self.client.get(
            f'{self.logout_url}?next=https://exploding-kittens.com/logout-confirm',
            HTTP_REFERER='https://exploding-kittens.com/')
        self.assertEqual(302, resp.status_code)
        self.assertEqual('https://exploding-kittens.com/logout-confirm', resp['Location'])


class LoginTest(TestCase):
    login_url = reverse('bid_main:login')
    authorize_url = reverse('oauth2_provider:authorize')

    def test_bid_login(self):
        """Logging in on Blender ID, not part of OAuth flow."""
        resp = self.client.get(self.login_url)
        self.assertEqual(200, resp.status_code)
        self.assertIn('One Account, Everything Blender', resp.content.decode())

    def test_oauth_login_happy(self):
        """Logging in on Blender ID as part of OAuth flow."""

        oauth_app = Application.objects.create(name="je moeder")
        next_url = self.authorize_url + '?' + urlencode({'client_id': oauth_app.client_id})
        resp = self.client.get(self.login_url + '?' + urlencode({'next': next_url}))
        self.assertEqual(200, resp.status_code)
        self.assertIn('Please sign in to continue to', resp.content.decode())
        self.assertIn(oauth_app.name, resp.content.decode())

    def test_oauth_unknown_client_id(self):
        next_url = self.authorize_url + '?' + urlencode({'client_id': 'nonexisting'})
        resp = self.client.get(self.login_url + '?' + urlencode({'next': next_url}))
        self.assertEqual(200, resp.status_code)
        self.assertIn('One Account, Everything Blender', resp.content.decode())
