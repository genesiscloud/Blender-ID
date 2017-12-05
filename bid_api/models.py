from django.db import models

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

    def __str__(self):
        return f'Webhook {self.name!r}'
