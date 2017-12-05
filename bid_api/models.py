import hashlib
import hmac
import logging

from django.db import models
import requests

WEBHOOK_TYPES = [
    ('USER_MODIFIED', 'User Modified'),
]


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
                                  help_text='Timeout for HTTP calls to this webhook.')

    def __str__(self):
        return f'Webhook {self.name!r}'

    def send(self, payload: bytes, session: requests.Session):
        """Sends a message to the webhook.

        The payload has to be encoded as bytes already. This is a performance
        thing; it allows one to encode the payload once and then send it to
        multiple webhooks.

        :param payload: the encoded JSON to send
        :param session: the Requests session to use for sending. This allows
            multiple webhooks to the same host to share a TCP/IP connection,
            and allows the caller control over the number of retries.
        """

        log = logging.getLogger(f'{__name__}.Webhook.send')

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
            resp.raise_for_status()
        except (IOError, OSError) as ex:
            log.warning('error calling hook %s: %s', self, ex)
