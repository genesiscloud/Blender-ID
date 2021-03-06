import copy
import functools
import json
import logging

from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver, Signal

from . import models

log = logging.getLogger(__name__)
UserModel = get_user_model()
user_email_changed = Signal(providing_args=['user', 'old_email'])

USER_SAVE_INTERESTING_FIELDS = {'email', 'full_name', 'public_roles_as_string', 'avatar'}
WEBHOOK_TIMEOUT_SECS = 5


def filter_user_save_hook(wrapped):
    """Decorator for the webhook user-save signal handlers."""

    @functools.wraps(wrapped)
    def wrapper(sender, instance, *args, **kwargs):
        if sender != UserModel or not isinstance(instance, UserModel):
            # log.debug('skipping save of sender %r', sender)
            return

        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            # log.debug('User %s was saved on fields %r only', instance.email, update_fields)
            if not set(update_fields).intersection(USER_SAVE_INTERESTING_FIELDS):
                # log.debug('User %s was modified only on ignored fields; ignoring', instance.email)
                return

        return wrapped(sender, instance, *args, **kwargs)

    return wrapper


def _check_user_modification(new_user: UserModel, old_user: UserModel) -> bool:
    """Returns True iff the user was modified.

    Only checks fields listed in USER_SAVE_INTERESTING_FIELDS.
    """

    for field in USER_SAVE_INTERESTING_FIELDS:
        old_val = getattr(old_user, field)
        new_val = getattr(new_user, field)
        if old_val != new_val:
            # log.debug('user %s changed field %r from %r to %r',
            #           new_user.email, field, old_val, new_val)
            return True
        # log.debug('user %s has unmutated field %r = %r = %r',
        #           new_user.email, field, old_val, new_val)
    return False


@receiver(pre_save)
@filter_user_save_hook
def inspect_modified_user(sender, user: UserModel, **kwargs):
    # update_fields = kwargs.get('update_fields')
    # log.debug('pre-save of %s, fields %s', user.email, update_fields)

    # Default to False
    user.webhook_user_modified = False

    if not user.id:
        # New user; don't notify the webhooks.
        # log.debug('%s is a new user (no ID yet), skipping', user.email)
        return
    try:
        db_user = UserModel.objects.get(id=user.id)
    except UserModel.DoesNotExist:
        # New user; don't notify the webhooks.
        # log.debug('%s is a new user (not in DB), skipping', user.email)
        return

    # Make sure that the post-save hook knows what the pre-save user looks like.
    user.webhook_pre_save = copy.deepcopy(db_user.__dict__)
    user.webhook_user_modified = _check_user_modification(user, db_user)


@receiver(post_save)
@filter_user_save_hook
def modified_user_to_webhooks(sender, user: UserModel, **kwargs):
    """Forwards modified user information to webhooks.

    The payload is POSTed, and a HMAC-SHA256 checksum is sent using the
    X-Webhook-HMAC HTTP header.

    Also see https://docs.djangoproject.com/en/1.11/ref/signals/#post-save
    """

    # update_fields = kwargs.get('update_fields')
    # log.debug('post-save of %s, fields %s', user.email, update_fields)

    if not getattr(user, 'webhook_user_modified', False):
        # log.debug('Skipping save of %s', user.email)
        return

    hooks = models.Webhook.objects.filter(enabled=True)
    log.debug('Sending modification of %s to %d webhooks', user.email, len(hooks))

    # Get the old email address so that the webhook receiver can match by
    # either database ID or email address.
    webhook_pre_save = getattr(user, 'webhook_pre_save', {})
    old_email = webhook_pre_save.get('email')

    # Map all falsey values to empty string for more consistent comparison later.
    # An empty avatar can be either '' or None.
    old_avatar = webhook_pre_save.get('avatar') or ''
    cur_avatar = user.avatar or ''

    if old_avatar and old_avatar != cur_avatar:
        log.debug('User changed avatar, going to delete old avatar file %r', old_avatar)
        default_storage.delete(old_avatar)

    if old_email != user.email:
        log.debug('User changed email from %s to %s', old_email, user.email)
        user_email_changed.send(sender, user=user, old_email=old_email)

    # Do our own JSON encoding so that we can compute the HMAC using the hook's secret.
    payload = {
        'id': user.id,
        'old_email': old_email,
        'full_name': user.get_full_name(),
        'email': user.email,
        'roles': sorted(user.public_roles()),
        'avatar_changed': old_avatar != cur_avatar,
    }
    json_payload = json.dumps(payload).encode()

    sess = models.webhook_session()
    for hook in hooks:
        log.debug('Sending to %s, %s', hook, hook.url)
        hook.send(json_payload, sess)
