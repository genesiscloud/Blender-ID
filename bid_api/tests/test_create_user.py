from datetime import timedelta
import json

from django.http import HttpResponse, HttpRequest
from django.contrib.admin.models import LogEntry
from django.core.urlresolvers import reverse
from django.utils import timezone

from .abstract import AbstractAPITest, AccessToken, UserModel


class CreateUserTest(AbstractAPITest):
    access_token_scope = 'usercreate'

    def post(self, data: dict, *, access_token='') -> HttpResponse:
        url_path = reverse('bid_api:create_user')
        response = self.authed_post(url_path, data=data, access_token=access_token)
        return response

    def assert_can_auth(self, email, password, expected_user_id):
        """Asserts that the given email/password combination is valid for the given user."""

        from django.contrib.auth import authenticate
        req = HttpRequest()
        authed_user = authenticate(req, username=email, password=password)
        self.assertIsNotNone(authed_user)
        self.assertTrue(authed_user.is_authenticated)
        self.assertEqual(authed_user.id, expected_user_id)

    def test_create_user_happy(self):
        test_email = 'test.complex+address-yay@user.nl'
        response = self.post({
            'email': test_email,
            'full_name': 'Ünicode Ǉepper',
            'password': 'the-real-password',
        })
        self.assertEqual(201, response.status_code, f'response: {response}')
        self.assertEqual('application/json', response.get('content-type'))

        db_user: UserModel = UserModel.objects.get(email=test_email)
        self.assertEqual('Ünicode Ǉepper', db_user.full_name)
        self.assertNotEqual('blenderid$the-real-password', db_user.password)
        self.assertEqual(test_email, db_user.email)
        self.assertEqual('Ünicode-Ǉepper', db_user.nickname)

        payload = json.loads(response.content)
        self.assertEqual({'user_id': db_user.id}, payload)

        # There should be a log entry describing the creation.
        entries = list(LogEntry.objects.filter(object_id=db_user.id))
        self.assertEqual(1, len(entries))

        # We should be able to authenticate with the password.
        self.assert_can_auth(test_email, 'the-real-password', db_user.id)

    def test_existing_username(self):
        test_email = 'test.complex+address-yay@user.nl'
        response = self.post({
            'email': 'other@example.com',
            'full_name': 'Ünicode Ǉepper',
            'password': 'the-real-password',
        })
        self.assertEqual(201, response.status_code, f'response: {response}')
        self.assertEqual('application/json', response.get('content-type'))

        # Test with same name, but different email. Name-based nick should clash.
        response = self.post({
            'email': test_email,
            'full_name': 'Ünicode Ǉepper',
            'password': 'the-real-password',
        })
        self.assertEqual(201, response.status_code, f'response: {response}')

        db_user: UserModel = UserModel.objects.get(email=test_email)
        self.assertEqual('Ünicode Ǉepper', db_user.full_name)
        self.assertNotEqual('blenderid$the-real-password', db_user.password)
        self.assertEqual(test_email, db_user.email)
        self.assertRegex(db_user.nickname, '^Ünicode-Ǉepper-[0-9]$')

        payload = json.loads(response.content)
        self.assertEqual({'user_id': db_user.id}, payload)

        # There should be a log entry describing the creation.
        entries = list(LogEntry.objects.filter(object_id=db_user.id))
        self.assertEqual(1, len(entries))

        # We should be able to authenticate with the password.
        self.assert_can_auth(test_email, 'the-real-password', db_user.id)

    def test_create_user_exists(self):
        response = self.post({
            'email': 'test@user.nl',
            'full_name': 'Ünicode Ǉepper',
            'password': 'the-real-password',
        })
        self.assertEqual(201, response.status_code, f'response: {response}')

        response = self.post({
            'email': 'test@user.nl',
            'full_name': 'Other',
            'password': '$2a$some-other-hash-here',
        })
        self.assertEqual(409, response.status_code, f'response: {response}')
        self.assertEqual('application/json', response.get('content-type'))
        self.assertEqual({
            'email': [{'code': 'unique',
                       'message': 'A user with that email address already exists.'}]},
            json.loads(response.content))

        # Existing user should not be modified.
        db_user: UserModel = UserModel.objects.get(email='test@user.nl')
        self.assertEqual('Ünicode Ǉepper', db_user.full_name)
        self.assertEqual('test@user.nl', db_user.email)
        self.assert_can_auth('test@user.nl', 'the-real-password', db_user.id)

    def test_missing_email(self):
        response = self.post({
            'full_name': 'Ünicode Ǉepper',
            'password': 'the-real-password',
        })
        self.assertEqual(400, response.status_code, f'response: {response}')
        self.assertEqual('application/json', response.get('content-type'))
        self.assertIn('email', json.loads(response.content))
        self.assert_no_user('')

    def test_missing_name(self):
        response = self.post({
            'email': 'test@email.com',
            'password': 'the-real-password',
        })
        self.assertEqual(201, response.status_code, f'response: {response}')

        db_user: UserModel = UserModel.objects.get(email='test@email.com')
        self.assertEqual('', db_user.full_name)
        self.assertEqual('test', db_user.nickname)

    def test_missing_password(self):
        response = self.post({
            'email': 'test@email.com',
            'full_name': 'Ünicode Ǉepper',
        })
        self.assertEqual(400, response.status_code, f'response: {response}')
        self.assertEqual('application/json', response.get('content-type'))
        self.assertIn('password', json.loads(response.content))
        self.assert_no_user('test@email.com')

    def test_bad_email(self):
        response = self.post({
            'email': 'aap noot mies op je hoofd',
            'full_name': 'Ünicode Ǉepper',
            'password': 'the-real-password',
        })
        self.assertEqual(400, response.status_code, f'response: {response}')
        self.assertEqual('application/json', response.get('content-type'))
        self.assertIn('email', json.loads(response.content))
        self.assert_no_user('aap noot mies op je hoofd')

    def test_create_user_bad_token_scope(self):
        wrong_token = AccessToken.objects.create(
            user=self.user,
            scope='email',
            expires=timezone.now() + timedelta(seconds=300),
            token='token-with-wrong-scope',
            application=self.application
        )
        wrong_token.save()
        response = self.post({
            'email': 'test@user.nl',
            'full_name': 'Ünicode Ǉepper',
            'password': 'the-real-password',
        }, access_token=wrong_token.token)
        self.assertEqual(403, response.status_code)
        self.assert_no_user('test@user.nl')

    def assert_no_user(self, email):
        with self.assertRaises(UserModel.DoesNotExist):
            UserModel.objects.get(email=email)


class CheckUserTest(AbstractAPITest):
    access_token_scope = 'usercreate'

    def get(self, email: str, *, access_token='') -> HttpResponse:
        url_path = reverse('bid_api:check_user', kwargs={'email': email})
        response = self.authed_get(url_path, access_token=access_token)
        return response

    def test_check_user_happy(self):
        # Existing user
        resp = self.get(self.user.email)
        self.assertEqual(200, resp.status_code)
        self.assertEqual({'found': True}, json.loads(resp.content))

        # Nonexisting user
        resp = self.get('nonexistent@nowhere.huh')
        self.assertEqual(200, resp.status_code)
        self.assertEqual({'found': False}, json.loads(resp.content))

    def test_bad_email(self):
        resp = self.get(f'{self.user.email}\x00\x00\xffhackhackhack')
        self.assertEqual(200, resp.status_code)
        self.assertEqual({'found': False}, json.loads(resp.content))

    def test_check_user_bad_token_scope(self):
        wrong_token = AccessToken.objects.create(
            user=self.user,
            scope='email',
            expires=timezone.now() + timedelta(seconds=300),
            token='token-with-wrong-scope',
            application=self.application
        )
        wrong_token.save()
        resp = self.get(self.user.email, access_token=wrong_token.token)
        self.assertEqual(403, resp.status_code)
