"""User registration, email change and confirmation."""
import logging

from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, TemplateView, FormView, View

from .. import forms, email
from ..models import User

log = logging.getLogger(__name__)


class RegistrationView(CreateView):
    form_class = forms.UserRegistrationForm
    model = User
    template_name_suffix = '_register_form'
    log = log.getChild('RegistrationForm')

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def form_valid(self, form: forms.UserRegistrationForm):
        try:
            with transaction.atomic():
                self.object = form.save(commit=False)
                self.object.set_password(User.objects.make_random_password())
                self.object.save()  # this actually saves the object and can raise an IntegrityError

                # This form only requires the "email" field, so will validate.
                reset_form = PasswordResetForm(self.request.POST)
                reset_form.is_valid()  # Must trigger validation

                # Copied from django/contrib/auth/views.py : password_reset
                opts = {
                    'use_https': self.request.is_secure(),
                    'email_template_name': 'registration/email_verification.txt',
                    'html_email_template_name': 'registration/email_verification.html',
                    'subject_template_name': 'registration/email_verification_subject.txt',
                    'request': self.request,
                    # 'html_email_template_name': provide an HTML content template if you desire.
                }
                # This form sends the email on save() and can raise a subclass of OSError.
                reset_form.save(**opts)

        except IntegrityError as ex:
            err = ValidationError(
                _('There was an error registering your account: %(ex)s. '
                  'This probably means you were already registered. If this is not the case, '
                  'and the error remains, contact us at cloudsupport@blender.org. Otherwise '
                  'just log in on your account.'),
                params={'ex': str(ex)},
                code='register-integrity-error'
            )
            form.add_error('email', err)
            log.warning('Integrity error trying to save user %s: %s', self.object, ex)
            return self.render_to_response(self.get_context_data(form=form))

        except OSError as ex:
            log.exception('Error sending registration email')
            err = ValidationError(
                _('There was an error sending your registration email (%(ex)s). '
                  'Your registration has been aborted and this error was logged. '
                  'Please try again later. If the error remains, contact us at '
                  'cloudsupport@blender.org'),
                params={'ex': str(ex)},
                code='mail-error'
            )
            form.add_error(None, err)
            return self.render_to_response(self.get_context_data(form=form))

        return redirect('bid_main:register-done')


class InitialSetPasswordView(auth_views.PasswordResetConfirmView):
    template_name = 'registration/initial_set_password.html'
    success_url = reverse_lazy('bid_main:register-complete')
    form_class = forms.SetInitialPasswordForm


class ConfirmEmailView(LoginRequiredMixin, FormView):
    template_name = 'bid_main/confirm_email/start.html'
    form_class = forms.ConfirmEmailStartForm
    log = logging.getLogger(f'{__name__}.ConfirmEmailView')

    def post(self, request, *args, **kwargs):
        user = request.user
        if user.email_change_preconfirm:
            self.log.info('Starting email change confirmation flow for user %s to %s',
                          user.email, user.email_change_preconfirm)
        else:
            self.log.info('Starting email confirmation flow for user %s', user.email)

        form = self.get_form()
        if not form.is_valid():
            self.log.warning('posted form is invalid: %s', form.errors.as_json())
            return HttpResponseBadRequest('Invalid data received')

        if form.cleaned_data['next_url'] and form.cleaned_data['next_name']:
            extra = {
                'n_url': form.cleaned_data['next_url'],
                'n_name': form.cleaned_data['next_name'],
            }
        else:
            extra = {}

        ok = email.send_verify_address(user, request.scheme, extra)
        if not ok:
            self.template_name = 'bid_main/confirm_email/smtp_error.html'
            return self.render_to_response({})
        return redirect('bid_main:confirm-email-sent')


class CancelEmailChangeView(LoginRequiredMixin, View):
    """Cancel the user's email change and redirect to the profile page."""
    log = logging.getLogger(f'{__name__}.CancelEmailChangeView')

    def post(self, request, *args, **kwargs):
        user = request.user
        self.log.info('User %s cancelled email change to %s', user, user.email_change_preconfirm)
        user.email_change_preconfirm = ''
        user.save()
        return redirect('bid_main:index')


class ConfirmEmailSentView(LoginRequiredMixin, TemplateView):
    template_name = 'bid_main/confirm_email/sent.html'


class ConfirmEmailPollView(LoginRequiredMixin, View):
    """Returns JSON indicating when the email address has last been confirmed.

    The timestamp is returned as ISO 8601 to allow future periodic checks
    (like a check every 6 months); in such a case a simple boolean wouldn't
    be enough.

    The timestamp is null if the user has not yet confirmed their email, or
    if they are confirming an email change. In the latter case there is a
    'confirmed_email_at' field that's already set, but irrelevant to this
    confirmation flow.
    """

    def get(self, request, *args, **kwargs):
        if request.user.email_change_preconfirm:
            timestamp = None
        else:
            timestamp = request.user.confirmed_email_at
        return JsonResponse({'confirmed': timestamp})


class ConfirmEmailVerifiedView(LoginRequiredMixin, TemplateView):
    """Render explanation on GET, handle confirmation on POST.

    We only perform the actual database change on a POST, since that protects
    from browsers that pre-fetch the page. The POST is done with some JS, I
    hope that isn't triggered on a pre-fetch.
    """
    template_name = 'bid_main/confirm_email/verified-happy.html'
    integrity_error_template_name = 'bid_main/confirm_email/integrity-error.html'
    log = log.getChild('ConfirmEmailVerifiedView')

    def _verify_request(self, request, kwargs):
        b64payload = kwargs.get('info', '')
        hmac = kwargs.get('hmac', '')
        user = request.user
        result, payload = email.check_verification_payload(b64payload, hmac, user.email_to_confirm)
        return result, payload

    def get(self, request, *args, **kwargs):
        result, payload = self._verify_request(request, kwargs)

        if result == email.VerificationResult.INVALID:
            return render(request, 'bid_main/confirm_email/verified-invalid.html', status=400)
        elif result == email.VerificationResult.OTHER_ACCOUNT:
            return render(request, 'bid_main/confirm_email/verified-other-account.html', {
                'payload': payload,
            })
        elif result == email.VerificationResult.EXPIRED:
            return render(request, 'bid_main/confirm_email/verified-expired.html')
        elif result != email.VerificationResult.OK:
            self.log.error('unknown validation result %r', result)
            raise ValueError('unknown validation result')

        # Refuse to give a name if there is no URL and vice versa.
        # We should either have both or none.
        next_url = payload.get('n_url', '')
        next_name = payload.get('n_name', '')
        if not (next_url and next_name):
            next_url = next_name = ''

        ctx = {
            'next_url': next_url or reverse_lazy('bid_main:index'),
            'next_name': next_name or 'Blender ID Dashboard',
        }

        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        result, payload = self._verify_request(request, kwargs)
        if result != email.VerificationResult.OK:
            # Just let the JS reload the page to get the actual error message.
            return JsonResponse({'_message': 'Validation error, reload the page',
                                 'reload': True}, status=422)

        try:
            self.confirm_email_address(request.user)
        except IntegrityError as ex:
            return JsonResponse({'_message': str(ex)}, status=500)
        return JsonResponse({'_message': 'OK!'})

    def confirm_email_address(self, user):
        """Update the user to set their email address as confirmed."""

        old_email = user.email
        if user.email_change_preconfirm:
            user.email = user.email_change_preconfirm
            user.email_change_preconfirm = ''

        user.confirmed_email_at = timezone.now()
        try:
            user.save()
        except IntegrityError:
            if user.email == old_email:
                self.log.exception('IntegrityError while saving user confirmed email is %s',
                                   user.email)
            else:
                self.log.exception('IntegrityError while confirming email change from %s to %s',
                                   old_email, user.email)
            raise

        self.log.info('Confirmed email of %s via explicit email confirmation.', user.email)

