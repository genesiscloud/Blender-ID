import datetime
import hashlib
import hmac
import json

import responses
from django.test import TestCase
from django.utils import timezone

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


class WebhookTest(WebhookBaseTest):
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
            user = UserModel.objects.create_user(f'test@{domain}', '123456',
                                                 nickname=f'test123-{domain}')
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
        cmd.handle(flush=True, verbosity=3, monitor=False)

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
    def test_queueing_after_failure(self):
        """When one item is queued, new items should also be queued to ensure order."""

        # No POST response set up, so hook wil fail and be queued.
        user = UserModel.objects.create_user('test@user.com', '123456')
        user.full_name = 'ဖန်စီဘောင်းဘီ'
        user.save()
        self.assertEqual(1, models.WebhookQueuedCall.objects.count())

        # Set up POST to fix the hook
        responses.add(responses.POST,
                      self.hook.url,
                      json={'status': 'success'},
                      status=200)

        # A new change should also be queued, even though the webhook can be reached.
        user.full_name = 'another name'
        user.save()
        self.assertEqual(2, models.WebhookQueuedCall.objects.count())

        # Flushing should work now.
        models.WebhookQueuedCall.flush_all()
        self.assertEqual(3, len(responses.calls))  # one failed + two successful calls
        self.assertEqual(0, models.WebhookQueuedCall.objects.count())

        # Another change should go through just fine.
        user.full_name = 'yet another name'
        user.save()
        self.assertEqual(4, len(responses.calls))  # one failed + three successful calls
        self.assertEqual(0, models.WebhookQueuedCall.objects.count())

    @responses.activate
    def test_email_changed_signal(self):
        received = []

        def store_signals(sender, signal, **kwargs):
            received.append((sender, signal, kwargs))

        signals.user_email_changed.connect(store_signals)
        responses.add(responses.POST,
                      self.hook.url,
                      json={'status': 'success'},
                      status=200)

        user = UserModel.objects.create_user('test@user.com', '123456')
        self.assertEqual([], received, 'User creation should not triggger email changed signal')

        expect_signal = (UserModel,
                         signals.user_email_changed,
                         {'user': user, 'old_email': 'test@user.com'})

        user.full_name = 'ဖန်စီဘောင်းဘီ'
        user.save()
        self.assertEqual([], received,
                         'Changing full name should not triggger email changed signal')

        user.email = 'new+email@user.com'
        user.save()
        self.assertEqual([expect_signal], received,
                         'Change of email should trigger email changed signal')
        received.clear()

        user.email = 'new+email@user.com'
        user.save()
        self.assertEqual([], received,
                         'Saving user without email change should not trigger email changed signal')


class WebhookFlushDelayTest(WebhookBaseTest):
    """To simplify the test, we use a fake 'now' for evaluation.

    This prevents setting queued_call.created after saving it and saving
    it again.
    """
    def queue_call(self):
        queued_call = models.WebhookQueuedCall(
            webhook=self.hook,
            payload='"payload"',
            error_code=0,
            error_msg='unit test',
        )
        queued_call.save()

    def test_empty_queue(self):
        flush_delay = self.hook.flush_delay()
        self.assertIsNone(flush_delay)

    def test_just_queued(self):
        self.queue_call()

        now = timezone.now()
        flush_delay = self.hook.flush_delay(now=now)
        self.assertEqual(flush_delay, datetime.timedelta(seconds=1))

    def test_queued_1_min_ago(self):
        self.queue_call()

        now = timezone.now() + datetime.timedelta(minutes=1)
        flush_delay = self.hook.flush_delay(now=now)
        self.assertEqual(flush_delay, datetime.timedelta(seconds=5))

    def test_queued_3_min_ago(self):
        self.queue_call()

        now = timezone.now() + datetime.timedelta(minutes=3)
        flush_delay = self.hook.flush_delay(now=now)
        self.assertEqual(flush_delay, datetime.timedelta(seconds=10))

    def test_queued_10_min_ago(self):
        self.queue_call()

        now = timezone.now() + datetime.timedelta(minutes=10)
        flush_delay = self.hook.flush_delay(now=now)
        self.assertEqual(flush_delay, datetime.timedelta(seconds=10))

    def test_queued_1_hour_ago(self):
        self.queue_call()

        now = timezone.now() + datetime.timedelta(hours=1)
        flush_delay = self.hook.flush_delay(now=now)
        self.assertEqual(flush_delay, datetime.timedelta(seconds=15))


class WebhookFlushTimeTest(WebhookBaseTest):

    def assertCloseTo(self, time1, time2, **kwargs):
        """Asserts that 'time1' is close to 'time2 + timedelta(**kwargs)'."""
        delta = datetime.timedelta(**kwargs)
        precision = datetime.timedelta(milliseconds=10)

        if time2 + delta - precision <= time1 <= time2 + delta + precision:
            return
        self.fail(f'{time1} is not close to {time2} + {delta}:\n'
                  f'Actual  : {time1}\n'
                  f'Expected: {time2+delta}')

    def queue_call(self, created: datetime.datetime):
        queued_call = models.WebhookQueuedCall(
            webhook=self.hook,
            payload='"payload"',
            error_code=0,
            error_msg='unit test',
        )
        queued_call.save()
        queued_call.created = created
        queued_call.save(update_fields={'created'})

    def test_empty_queue(self):
        flush_time = self.hook.flush_time()
        self.assertIsNone(flush_time)

    def test_just_queued_never_flushed(self):
        now = timezone.now()
        self.queue_call(now)

        flush_time = self.hook.flush_time(now=now)
        self.assertCloseTo(flush_time, now, seconds=0)

    def test_queued_47_min_ago_flushed_never(self):
        now = timezone.now()
        # Oldest queued call was queued 47 minutes ago.
        self.queue_call(now - datetime.timedelta(minutes=47))

        # Verify that the creation timestamp was set correctly.
        oldest = self.hook.queue.order_by('created').first()
        age = now - oldest.created
        self.assertEqual(47 * 60, age.total_seconds())

        # Should be flushed soon.
        flush_time = self.hook.flush_time(now=now)
        self.assertCloseTo(flush_time, now, seconds=0)

    def test_queued_47_min_ago_flushed_3_sec_ago(self):
        now = timezone.now()
        # Oldest queued call was queued 47 minutes ago.
        self.queue_call(now - datetime.timedelta(minutes=47))

        # Last flush was 3 seconds ago.
        self.hook.last_flush_attempt = now - datetime.timedelta(seconds=3)
        self.hook.save()

        # Should be flushed 15 seconds after last flush.
        flush_delay = self.hook.flush_delay(now=now)
        self.assertEqual(datetime.timedelta(seconds=15), flush_delay)

        flush_time = self.hook.flush_time(now=now)
        self.assertCloseTo(flush_time, now, seconds=12)


    def test_more_queued_47_min_ago_flushed_3_sec_ago(self):
        now = timezone.now()
        # Oldest queued call was queued 47 minutes ago.
        self.queue_call(now - datetime.timedelta(minutes=47))
        # But there are others that are more recent. They should not have an effect.
        self.queue_call(now - datetime.timedelta(minutes=13))
        self.queue_call(now - datetime.timedelta(seconds=10))

        # Last flush was 3 seconds ago.
        self.hook.last_flush_attempt = now - datetime.timedelta(seconds=3)
        self.hook.save()

        # Should be flushed 15 seconds after last flush.
        flush_delay = self.hook.flush_delay(now=now)
        self.assertEqual(datetime.timedelta(seconds=15), flush_delay)

        flush_time = self.hook.flush_time(now=now)
        self.assertCloseTo(flush_time, now, seconds=12)
