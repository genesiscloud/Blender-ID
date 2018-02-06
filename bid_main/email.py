import logging

from django.dispatch import receiver

from bid_api import signals as api_signals

log = logging.getLogger(__name__)


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
