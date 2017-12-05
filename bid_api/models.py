import hashlib
import hmac
import logging

from django.db import models
import requests

WEBHOOK_TYPES = [
    ('USER_MODIFIED', 'User Modified'),
]
WEBHOOK_RETRY_COUNT = 5


def webhook_session() -> requests.Session:
    """Creates a Requests session for sending to webhooks."""
    import requests.adapters

    sess = requests.Session()
    sess.mount('https://', requests.adapters.HTTPAdapter(max_retries=5))
    sess.mount('http://', requests.adapters.HTTPAdapter(max_retries=5))
    return sess


def create_random_secret() -> str:
    import secrets

    return secrets.token_urlsafe(32)


class Webhook(models.Model):
    name = models.CharField(max_length=128)
    enabled = models.BooleanField(default=True)
    hook_type = models.CharField(max_length=32, choices=WEBHOOK_TYPES, default=WEBHOOK_TYPES[0][0],
                                 db_index=True)
    url = models.URLField()
    secret = models.CharField(max_length=64, default=create_random_secret)
    description = models.TextField(blank=True,
                                   help_text='Description of this webhook, for staff-eyes only.')
    timeout = models.IntegerField(default=3,
                                  help_text='Timeout for HTTP calls to this webhook, in seconds.')

    def __str__(self):
        return self.name

    def queue_size(self) -> int:
        """Returns the number of queued calls to this webhook."""
        return self.queue.count()

    def send(self, payload: bytes, session: requests.Session,
             *, queued: 'WebhookQueuedCall' = None):
        """Sends a message to the webhook.

        The payload has to be encoded as bytes already. This is a performance
        thing; it allows one to encode the payload once and then send it to
        multiple webhooks.

        :param payload: the encoded JSON to send
        :param session: the Requests session to use for sending. This allows
            multiple webhooks to the same host to share a TCP/IP connection,
            and allows the caller control over the number of retries.
        :param queued: the WebhookQueuedCall that's being sent now. When None
            (the default) a failure to send will create a new item in the
            queue. When not None, a failure will be recorded on 'queued'
            instead.
        """
        log = logging.getLogger(f'{__name__}.Webhook.send')

        def record_error(status_code: int, error_msg: str):
            """Records an error by either creating a new queued call or updating one."""
            nonlocal queued

            if queued is None:
                # We re-decode the JSON payload, so that we can show it in the admin while queued.
                queued = WebhookQueuedCall(
                    webhook=self,
                    payload=payload.decode(),
                    error_code=status_code,
                    error_msg=error_msg,
                )
            else:
                queued.error_code = status_code
                queued.error_msg = error_msg
            queued.save()

        mac = hmac.new(self.secret.encode(), payload, hashlib.sha256)
        try:
            log.debug('sending to %s', self.url)
            resp = session.post(
                self.url,
                data=payload,
                headers={
                    'Content-Type': 'application/json',
                    'X-Webhook-HMAC': mac.hexdigest(),
                },
                timeout=self.timeout,
            )
            if resp.status_code >= 400:
                log.warning('error calling hook %s, HTTP %s, queueing', self, resp.status_code)
                record_error(resp.status_code, resp.text or '')
                return
        except (IOError, OSError) as ex:
            log.warning('error calling hook %s, queueing: %s', self, ex)
            record_error(0, str(ex))
            return

        # If we're here, the send was a success.
        if queued:
            log.info('dequeueing webhook call to %s', self.url)
            queued.delete()


class WebhookQueuedCall(models.Model):
    """Queued call to a webhook.

    Ordinarily webhooks are called immediately, but when that fails the
    POST request is stored in this queue.
    """

    webhook = models.ForeignKey(Webhook, on_delete=models.CASCADE, related_name='queue')
    payload = models.TextField(help_text='The payload to POST to the webhook')

    error_code = models.IntegerField(blank=True,
                                     help_text='The HTTP status code received when POSTing')
    error_msg = models.TextField(blank=True,
                                 help_text='The HTTP response received when POSTing')

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Webhook Queued Call'
        verbose_name_plural = 'Webhook queue'

    @classmethod
    def flush_all(cls):
        """Tries to deliver all queued calls."""
        log = logging.getLogger(f'{__name__}.WebhookQueuedCall.flush_all')
        queued_count = cls.objects.count()
        if queued_count == 0:
            log.debug('nothing to flush')
            return

        log.info('flushing %d queued item(s)', queued_count)
        # Order by 'created' to keep items in the correct order. This is important
        # for subscription statuses for example (the store takes away the subscription
        # role when payment is due, and gives it back when paid, and those should be
        # handled in the correct order).
        sess = webhook_session()
        for item in cls.objects.order_by('created'):
            payload = item.payload.encode()
            item.webhook.send(payload, sess, queued=item)
