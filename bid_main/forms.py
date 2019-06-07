import logging
import pathlib

from django import forms
from django.conf import settings
from django.contrib.auth import forms as auth_forms
from django.template import defaultfilters
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from .models import User

log = logging.getLogger(__name__)


class BootstrapModelFormMixin:
    """Adds the Bootstrap CSS class 'form-control' to all form fields."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        kwargs.setdefault('label_suffix', '')

        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'


class UserRegistrationForm(BootstrapModelFormMixin, forms.ModelForm):
    # This class uses 'bid_main/user_register_form.html' to render
    class Meta:
        model = User
        fields = ['full_name', 'email', 'nickname']


class SetInitialPasswordForm(BootstrapModelFormMixin, auth_forms.SetPasswordForm):
    """Used when setting password in user registration flow.

    This means that the user has clicked on a link sent by email, so this
    confirms their email address.
    """

    def save(self, commit=True):
        self.user.confirmed_email_at = timezone.now()
        log.info('Confirmed email of %s through initial password form.', self.user.email)

        return super().save(commit=commit)


class AuthenticationForm(BootstrapModelFormMixin, auth_forms.AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        email_widget = forms.EmailInput(attrs={'autofocus': True,
                                               'placeholder': 'Your email address',
                                               'class': 'form-control'})
        self.fields['username'].widget = email_widget
        self.fields['password'].widget.attrs['placeholder'] = 'Your password'


class UserProfileForm(BootstrapModelFormMixin, forms.ModelForm):
    """Edits full name and email address.

    Works with the 'email' field directly, for validation, error messages, etc.
    but saves the actual changed email to the 'email_change_preconfirm' model
    field.
    """
    log = log.getChild('UserProfileForm')

    class Meta:
        model = User
        fields = ['full_name', 'email', 'nickname', 'avatar']

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        if instance is None:
            raise ValueError('This form can only be used for existing users.')
        # Store the current email address before _post_clean() overwrites it
        # with the email address from the form.
        self._original_email = instance.email

        super().__init__(*args, **kwargs)

        # Refuse to edit the email address while another change is still pending.
        if instance.email_change_preconfirm:
            self.fields['email'].disabled = True

    def clean_full_name(self):
        full_name = self.cleaned_data['full_name'].strip()
        if not full_name:
            raise forms.ValidationError(_('Full Name is a required field'))
        return full_name

    def clean_email(self):
        """Don't allow direct changes to the email address, only to the preconfirm one."""
        form_email = self.cleaned_data['email']

        if self._original_email == form_email:
            self.log.debug('%s updated their profile', form_email)
            return form_email

        self.log.info('User %s wants to change their email to %s', self._original_email, form_email)
        self.instance.email = self._original_email
        self.instance.email_change_preconfirm = form_email
        return self._original_email

    def clean_nickname(self):
        nickname = self.cleaned_data['nickname'].strip()
        if not nickname:
            raise forms.ValidationError(_('Nickname is a required field'))
        return nickname

    def clean_avatar(self):
        data = self.cleaned_data['avatar']
        if isinstance(data, bool) or not data:
            # Bool data happens when the user checks the 'clean' checkbox.
            # None happens when there is no avatar.
            return data

        filename = pathlib.PurePath(data.name)
        if filename.suffix.lower() not in settings.AVATAR_ALLOWED_FILE_EXTS:
            valid_exts = ", ".join(sorted(settings.AVATAR_ALLOWED_FILE_EXTS))
            error = _("%(ext)s is not an allowed file extension. "
                      "Authorized extensions are : %(valid_exts_list)s")
            raise forms.ValidationError(error %
                                        {'ext': filename.suffix,
                                         'valid_exts_list': valid_exts})

        if data.size > settings.AVATAR_MAX_SIZE_BYTES:
            error = _("Your file is too big (%(size)s), "
                      "the maximum allowed size is %(max_valid_size)s")
            raise forms.ValidationError(error % {
                'size': defaultfilters.filesizeformat(data.size),
                'max_valid_size': defaultfilters.filesizeformat(settings.AVATAR_MAX_SIZE_BYTES)
            })

        return data


class PasswordChangeForm(BootstrapModelFormMixin, auth_forms.PasswordChangeForm):
    """Password change form with Bootstrap CSS classes."""


class PasswordResetForm(BootstrapModelFormMixin, auth_forms.PasswordResetForm):
    """Password reset form with Bootstrap CSS classes."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs['placeholder'] = 'Your email address'


class AppRevokeTokensForm(forms.Form):
    """Form for revoking OAuth tokens for a specific application."""

    app_id = forms.IntegerField(widget=forms.HiddenInput)


class ConfirmEmailStartForm(forms.Form):
    """Hidden fields for the email confirmation process."""

    next_url = forms.CharField(max_length=1024, widget=forms.HiddenInput, required=False)
    next_name = forms.CharField(max_length=1024, widget=forms.HiddenInput, required=False)


class PrivacyPolicyAgreeForm(forms.Form):
    agree = forms.BooleanField(
        initial=False,
        help_text='Check to agree with our privacy policy',
    )
    next_url = forms.CharField(max_length=1024, widget=forms.HiddenInput, required=False)
