import logging

from django.db.models import F
from django.core.signals import got_request_exception
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from . import models
from bid_api import signals as api_signals

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


@receiver(api_signals.user_email_changed)
def user_email_changed(sender, signal, *, user, old_email, **kwargs):
    """Sends out an email to the old & new address."""

    import smtplib
    from django.core.mail import send_mail

    email_body_html, email_body_txt, subject = construct_email_changed_mail(user, old_email)

    try:
        send_mail(
            subject,
            message=email_body_txt,
            html_message=email_body_html,
            from_email=None,  # just use the configured default From-address.
            recipient_list=[user.email, old_email],
            fail_silently=False,
        )
    except smtplib.SMTPException:
        log.exception('error sending email-changed notification to %s and %s',
                      user.email, old_email)
    else:
        log.info('sent email-changed notification to %s and %s',
                 user.email, old_email)


def construct_email_changed_mail(user, old_email) -> (str, str, str):
    from django.template import loader
    from django.contrib.sites.shortcuts import get_current_site
    from django.urls import reverse

    # Construct the link to Blender ID dynamically, to prevent hard-coding it in the email.
    # TODO(Sybren): move this to a more suitable spot so we can use it elsewhere too.
    domain = get_current_site(None).domain
    url = reverse('bid_main:index')

    context = {
        'user': user,
        'old_email': old_email,
        'blender_id': f'https://{domain}{url}',
        'subject': 'Blender ID email change',
    }

    email_body_html = loader.render_to_string('bid_main/emails/user_email_changed.html', context)
    email_body_txt = loader.render_to_string('bid_main/emails/user_email_changed.txt', context)

    return email_body_html, email_body_txt, context['subject']
