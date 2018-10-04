from django.core.urlresolvers import reverse
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
