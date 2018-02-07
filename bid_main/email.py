import base64
import binascii
import datetime
import enum
import hashlib
import hmac
import json
import logging
import smtplib

import dateutil.parser
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.dispatch import receiver
from django.template import loader
from django.urls import reverse
from django.utils import timezone

from bid_api import signals as api_signals

log = logging.getLogger(__name__)


@receiver(api_signals.user_email_changed)
def user_email_changed(sender, signal, *, user, old_email, **kwargs):
    """Sends out an email to the old & new address."""

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


def send_verify_address(user, scheme: str, extra: dict=None):
    """Send out an email with address verification link.

    :param user: the user object whose email needs verification
    :param scheme: either 'http' or 'https', for link generation.
    :param extra: extra payload to store in the link JSON.
    """

    email_body_html, email_body_txt, subject = construct_verify_address(user, scheme, extra)

    email = user.email_to_confirm
    try:
        send_mail(
            subject,
            message=email_body_txt,
            html_message=email_body_html,
            from_email=None,  # just use the configured default From-address.
            recipient_list=[email],
            fail_silently=False,
        )
    except smtplib.SMTPException:
        log.exception('error sending address verification mail to %s', email)
    else:
        log.info('sent address verification mail to %s', email)


def _email_verification_hmac(payload: bytes) -> hmac.HMAC:
    return hmac.new(settings.SECRET_KEY.encode(), payload, hashlib.sha1)


def construct_verify_address(user, scheme: str, extra: dict=None) -> (str, str, str):
    """Construct the mail to verify an email address.

    :param user: the user object whose email needs verification
    :param scheme: either 'http' or 'https', for link generation.
    :param extra: extra payload to store in the link JSON.
    :returns: a tuple (html, text, subject) with the email contents.
    """
    # Construct the link to Blender ID dynamically, to prevent hard-coding it in the email.
    # TODO(Sybren): move this to a more suitable spot so we can use it elsewhere too.
    domain = get_current_site(None).domain

    # Construct an expiring URL that we can verify later. Doing it with an
    # HMAC makes it possible to verify without having to save anything to
    # the database.
    expire = timezone.now() + datetime.timedelta(hours=13)
    verification_payload = {
        'e': user.email_to_confirm,
        'x': expire.isoformat(timespec='minutes'),
        **(extra or {})
    }
    info = json.dumps(verification_payload).encode()
    b64info = base64.urlsafe_b64encode(info)
    hmac_ob = _email_verification_hmac(b64info)

    url = reverse('bid_main:confirm-email-verified', kwargs={
        'info': b64info,
        'hmac': hmac_ob.hexdigest()
    })

    context = {
        'user': user,
        'url': f'{scheme}://{domain}{url}',
        'subject': 'Blender ID email verification',
    }
    log.debug('Sending email confirm link %s to %s', url, user.email)

    email_body_html = loader.render_to_string('bid_main/emails/confirm_email.html', context)
    email_body_txt = loader.render_to_string('bid_main/emails/confirm_email.txt', context)

    return email_body_html, email_body_txt, context['subject']


class VerificationResult(enum.Enum):
    OK = 0
    EXPIRED = 1
    INVALID = 2  # invalid Base64, HMAC, JSON, or email address


def check_verification_payload(info_b64: str, expected_hmac: str,
                               expected_email: str) -> (VerificationResult, dict):
    """Check the HMAC and decode the info to check for expiry.

    :returns: the verification result and the info that was JSON+b64 encoded.
        The latter is just an empty dict when INVALID is returned.
    """

    my_log = log.getChild(f'check_verification_payload.{expected_email}')

    hmac_ob = _email_verification_hmac(info_b64.encode())
    actual_hmac = hmac_ob.hexdigest()
    if not hmac.compare_digest(actual_hmac, expected_hmac):
        my_log.warning('invalid HMAC, payload=%r, expected HMAC=%r, got %r',
                       info_b64, expected_hmac, actual_hmac)
        return VerificationResult.INVALID, {}

    try:
        info = base64.urlsafe_b64decode(info_b64)
    except (binascii.Error, ValueError):
        my_log.warning('invalid Base64: %r', info_b64)
        return VerificationResult.INVALID, {}

    try:
        payload = json.loads(info)
    except (TypeError, ValueError, UnicodeDecodeError):
        my_log.warning('invalid JSON, payload=%r', info, exc_info=True)
        return VerificationResult.INVALID, {}

    email = payload.get('e', '')
    if email != expected_email:
        my_log.warning('email does not match payload %r', email)
        return VerificationResult.INVALID, {}

    now = timezone.now()
    expiry = dateutil.parser.parse(payload.get('x', '')).replace(tzinfo=timezone.utc)
    if expiry < now:
        my_log.warning('link expired at %s', expiry)
        return VerificationResult.EXPIRED, payload

    log.debug('verification OK')
    return VerificationResult.OK, payload
