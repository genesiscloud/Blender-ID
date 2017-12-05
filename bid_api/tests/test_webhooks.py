import hashlib
import hmac
import json

import responses
from django.test import TestCase

from .abstract import UserModel
from bid_main.models import Role
from bid_api import models

# Import for side-effects of registering the signals
# noinspection PyUnresolvedReferences
from bid_api import signals


class WebhookBaseTest(TestCase):
    HOOK_URL = 'http://www.unit.test/api/webhook'

    def setUp(self):
        self.hook = models.Webhook(
            name='Unit test webhook',
            enabled=True,
            hook_type='USER_MODIFIED',
            url=self.HOOK_URL,
            secret='ieBithiGhahh4hee5mac8zu0xiu8kae0',
        )
        self.hook.save()
        super().setUp()

    @responses.activate
    def test_modify_user_email_only(self):
        responses.add(responses.POST,
                      self.HOOK_URL,
                      json={'status': 'success'},
                      status=200)

        user = UserModel.objects.create_user('test@user.com', '123456')
        user.email = 'new@user.com'
        user.save(update_fields={'email'})
        self.assertEqual(user.public_roles_as_string, '')

        self.assertTrue(user.webhook_user_modified)

        self.assertEqual(1, len(responses.calls))
        call = responses.calls[0]
        self.assertEqual(self.HOOK_URL, call.request.url)

        payload = json.loads(call.request.body)
        self.assertEqual({'id': user.id,
                          'old_email': 'test@user.com',
                          'full_name': '',
                          'email': 'new@user.com',
                          'roles': []},
                         payload)

        # This is just a stupid copy of the actual code, but I have no other way to
        # test the actual HMAC, apart from hardcoding a specific value (which is very
        # fragile, and frankly also simply copied from the output of the actual code).
        mac = hmac.new(self.hook.secret.encode('ascii'), call.request.body, hashlib.sha256)
        hexdigest = mac.hexdigest()

        self.assertEqual(hexdigest, call.request.headers['X-Webhook-HMAC'])
        self.assertEqual('application/json', call.request.headers['Content-Type'])

    @responses.activate
    def test_modify_user_email_and_full_name(self):
        responses.add(responses.POST,
                      self.HOOK_URL,
                      json={'status': 'success'},
                      status=200)

        user = UserModel.objects.create_user('test@user.com', '123456')
        user.email = 'new@user.com'
        user.full_name = 'ဖန်စီဘောင်းဘီ'
        user.save()

        self.assertTrue(user.webhook_user_modified)

        self.assertEqual(1, len(responses.calls))
        payload = json.loads(responses.calls[0].request.body)
        self.assertEqual({'id': user.id,
                          'old_email': 'test@user.com',
                          'full_name': 'ဖန်စီဘောင်းဘီ',
                          'email': 'new@user.com',
                          'roles': []},
                         payload)

    @responses.activate
    def test_modify_user_add_role(self):
        responses.add(responses.POST,
                      self.HOOK_URL,
                      json={'status': 'success'},
                      status=200)

        user = UserModel.objects.create_user('test@user.com', '123456', full_name='ဖန်စီဘောင်းဘီ')
        role1 = Role(name='cloud_subscriber',
                     is_public=True, is_badge=True, is_active=True)
        role1.save()
        role2 = Role(name='admin',
                     is_public=False, is_badge=False, is_active=True)
        role2.save()
        role3 = Role(name='cloud_single_member',
                     is_public=False, is_badge=False, is_active=False)
        role3.save()

        user.roles.add(role1)
        user.roles.add(role2)
        user.roles.add(role3)
        user.save()
        self.assertEqual('cloud_subscriber', user.public_roles_as_string)

        # Removing a public role should trigger the webhook.
        user.roles.remove(role1)
        user.save()
        self.assertEqual('', user.public_roles_as_string)

        # Removing a private role should not trigger the webhook.
        user.roles.remove(role2)
        user.save()

        self.assertEqual(2, len(responses.calls))
        payload = json.loads(responses.calls[0].request.body)
        self.assertEqual({'id': user.id,
                          'old_email': 'test@user.com',
                          'full_name': 'ဖန်စီဘောင်းဘီ',
                          'email': 'test@user.com',
                          'roles': ['cloud_subscriber']},
                         payload)
        payload = json.loads(responses.calls[1].request.body)
        self.assertEqual({'id': user.id,
                          'old_email': 'test@user.com',
                          'full_name': 'ဖန်စီဘောင်းဘီ',
                          'email': 'test@user.com',
                          'roles': []},
                         payload)

    @responses.activate
    def test_queue_after_error_500(self):
        responses.add(responses.POST,
                      self.HOOK_URL,
                      json={'status': 'error'},
                      status=500)

        user = UserModel.objects.create_user('test@user.com', '123456')
        user.full_name = 'ဖန်စီဘောင်းဘီ'
        user.save()

        # The POST to the webhook should be queued now.
        queue = list(models.WebhookQueuedCall.objects.all())
        self.assertEqual(1, len(queue))

        queued: models.WebhookQueuedCall = queue[0]
        self.assertEqual(500, queued.error_code)
        self.assertEqual('{"status": "error"}', queued.error_msg)

        payload = json.loads(queued.payload)
        self.assertEqual({'id': user.id,
                          'old_email': 'test@user.com',
                          'full_name': 'ဖန်စီဘောင်းဘီ',
                          'email': 'test@user.com',
                          'roles': []},
                         payload,
                         'The payload in the queue should be the POSTed JSON')

    @responses.activate
    def test_queue_after_ioerror(self):
        # Explicitly do not call responses.add(), so that it'll cause an error.

        user = UserModel.objects.create_user('test@user.com', '123456')
        user.full_name = 'ဖန်စီဘောင်းဘီ'
        user.save()

        # The POST to the webhook should be queued now.
        queue = list(models.WebhookQueuedCall.objects.all())
        self.assertEqual(1, len(queue))

        queued: models.WebhookQueuedCall = queue[0]
        self.assertEqual(0, queued.error_code)
        self.assertEqual('Connection refused: POST http://www.unit.test/api/webhook',
                         queued.error_msg)

        payload = json.loads(queued.payload)
        self.assertEqual({'id': user.id,
                          'old_email': 'test@user.com',
                          'full_name': 'ဖန်စီဘောင်းဘီ',
                          'email': 'test@user.com',
                          'roles': []},
                         payload,
                         'The payload in the queue should be the POSTed JSON')

    @responses.activate
    def test_flushing_queue_happy(self):
        # Expect the hook at a new URL.
        new_hook_url = self.HOOK_URL.replace('webhook', 'webhooks/user-changed')
        responses.add(responses.POST,
                      new_hook_url,
                      json={'status': 'success'},
                      status=200)

        user = UserModel.objects.create_user('test@user.com', '123456')
        user.full_name = 'ဖန်စီဘောင်းဘီ'
        user.save()

        # The POST to the webhook should be queued now.
        queue = list(models.WebhookQueuedCall.objects.all())
        self.assertEqual(1, len(queue))
        self.assertEqual(1, len(responses.calls))  # the failed call

        # Change some parameters to "fix" the hook.
        self.hook.secret = 'new-secret'
        self.hook.url = new_hook_url
        self.hook.save()

        # The queue flush should work at the new URL and use the new secret.
        models.WebhookQueuedCall.flush_all()

        self.assertEqual(2, len(responses.calls))  # the failed + the successful call
        call = responses.calls[1]
        self.assertEqual(new_hook_url, call.request.url)

        payload = json.loads(call.request.body)
        self.assertEqual({'id': user.id,
                          'old_email': 'test@user.com',
                          'full_name': 'ဖန်စီဘောင်းဘီ',
                          'email': 'test@user.com',
                          'roles': []},
                         payload)

        mac = hmac.new(b'new-secret', call.request.body, hashlib.sha256)
        hexdigest = mac.hexdigest()
        self.assertEqual(hexdigest, call.request.headers['X-Webhook-HMAC'])
        self.assertEqual('application/json', call.request.headers['Content-Type'])

        # The queue should be empty now.
        self.assertEqual(0, models.WebhookQueuedCall.objects.count())

    @responses.activate
    def test_flushing_queue_fails(self):
        import time

        # Expect the hook at a new URL.
        new_hook_url = self.HOOK_URL.replace('webhook', 'webhooks/user-changed')
        responses.add(responses.POST,
                      new_hook_url,
                      json={'status': 'success'},
                      status=200)

        user = UserModel.objects.create_user('test@user.com', '123456')
        user.full_name = 'ဖန်စီဘောင်းဘီ'
        user.save()

        # The POST to the webhook should be queued now.
        queue = list(models.WebhookQueuedCall.objects.all())
        self.assertEqual(1, len(queue))
        self.assertEqual(1, len(responses.calls))  # the failed call

        old_timestamp = queue[0].updated

        time.sleep(1)  # sleep for a second so that the change in 'updated' can be seen.
        models.WebhookQueuedCall.flush_all()

        # Flushing will fail, but should not create more queued items.
        queue = list(models.WebhookQueuedCall.objects.all())
        self.assertEqual(1, len(queue))

        # The updated timestamp should be, well, updated.
        self.assertGreater(queue[0].updated, old_timestamp)

    @responses.activate
    def test_flushing_larger_queue(self):
        """Test that we can flush three items at once."""

        # Update three users, causing three failed webhook calls.
        for domain in ('user1.com', 'user2.com', 'user3.com'):
            user = UserModel.objects.create_user(f'test@{domain}', '123456')
            user.email = f'new@{domain}'
            user.save(update_fields={'email'})
        self.assertEqual(3, models.WebhookQueuedCall.objects.count())

        # Website comes up again, flushing will succeed.
        responses.add(responses.POST,
                      self.hook.url,
                      json={'status': 'success'},
                      status=200)

        models.WebhookQueuedCall.flush_all()
        self.assertEqual(0, models.WebhookQueuedCall.objects.count())

    @responses.activate
    def test_flushing_queue_via_cli_cmd_happy(self):
        # Expect the hook at a new URL.
        new_hook_url = self.HOOK_URL.replace('webhook', 'webhooks/user-changed')
        responses.add(responses.POST,
                      new_hook_url,
                      json={'status': 'success'},
                      status=200)

        user = UserModel.objects.create_user('test@user.com', '123456')
        user.full_name = 'ဖန်စီဘောင်းဘီ'
        user.save()

        # The POST to the webhook should be queued now.
        queue = list(models.WebhookQueuedCall.objects.all())
        self.assertEqual(1, len(queue))
        self.assertEqual(1, len(responses.calls))  # the failed call

        # Change some parameters to "fix" the hook.
        self.hook.secret = 'new-secret'
        self.hook.url = new_hook_url
        self.hook.save()

        # The queue flush should work at the new URL and use the new secret.
        from bid_api.management.commands import flush_webhooks

        cmd = flush_webhooks.Command()
        cmd.handle(flush=True, verbosity=3)

        self.assertEqual(2, len(responses.calls))  # the failed + the successful call
        call = responses.calls[1]
        self.assertEqual(new_hook_url, call.request.url)

        payload = json.loads(call.request.body)
        self.assertEqual({'id': user.id,
                          'old_email': 'test@user.com',
                          'full_name': 'ဖန်စီဘောင်းဘီ',
                          'email': 'test@user.com',
                          'roles': []},
                         payload)

        mac = hmac.new(b'new-secret', call.request.body, hashlib.sha256)
        hexdigest = mac.hexdigest()
        self.assertEqual(hexdigest, call.request.headers['X-Webhook-HMAC'])
        self.assertEqual('application/json', call.request.headers['Content-Type'])

        # The queue should be empty now.
        self.assertEqual(0, models.WebhookQueuedCall.objects.count())
