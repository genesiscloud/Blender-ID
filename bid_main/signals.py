import logging

from django.db.models import F
from django.conf import settings
from django.core.signals import got_request_exception
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from . import models

log = logging.getLogger(__name__)


@receiver(got_request_exception)
def log_exception(sender, **kwargs):
    log.exception('uncaught exception occurred')


@receiver(user_logged_in)
def update_user_for_login(sender, request, user, **kwargs):
    """Updates user fields upon login.

    Only saves specific fields, so that the webhook trigger knows what changed.
    """

    log.debug('User %s logged in, storing login information', user.email)
    user.login_count = F('login_count') + 1
    fields = {'login_count'}

    # Only move 'current' to 'last' login IP if the IP address is different.
    request_ip = request.META.get('REMOTE_ADDR')
    if request_ip and user.current_login_ip != request_ip:
        user.last_login_ip = F('current_login_ip')
        user.current_login_ip = request_ip

        fields.update({'last_login_ip', 'current_login_ip'})

    user.save(update_fields=fields)


@receiver(m2m_changed)
def modified_user_role(sender, instance, action, reverse, model, **kwargs):
    my_log = log.getChild('modified_user_role')
    if not action.startswith('post_'):
        my_log.debug('Ignoring m2m %r on %s - %s', action, type(instance), model)
        return
    if not isinstance(instance, models.User) or not issubclass(model, models.Role):
        my_log.debug('Ignoring m2m %r on %s - %s', action, type(instance), model)
        return
    if not instance.id:
        my_log.debug('Ignoring m2m %r on %s (no ID) - %s', action, type(instance), model)
        return

    # User's roles changed, so we have to update their public_roles_as_string.
    new_roles = ' '.join(sorted(instance.public_roles()))
    if new_roles != instance.public_roles_as_string:
        instance.public_roles_as_string = new_roles
        my_log.debug('    saving user again for new roles %r', new_roles)
        instance.save(update_fields=['public_roles_as_string'])
    else:
        my_log.debug('    new roles are old roles: %r', new_roles)
