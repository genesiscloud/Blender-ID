import logging

from django.db.models import F
from django.core.signals import got_request_exception
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

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
