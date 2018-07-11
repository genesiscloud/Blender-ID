import functools
import typing

from django.db import models
from django.conf import settings
from django.core import validators, urlresolvers
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.utils import timezone
from django.utils.deconstruct import deconstructible
from django.utils.translation import ugettext_lazy as _

import oauth2_provider.models as oa2_models


class UserManager(BaseUserManager):
    """UserManager that doesn't use a username, but an email instead."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


@deconstructible
class UnicodeNicknameValidator(validators.RegexValidator):
    regex = r'^[\w.+-]+$'
    message = _(
        'Enter a valid nickname. This value may contain only letters, '
        'numbers, and ./+/-/_ characters.'
    )


class User(AbstractBaseUser, PermissionsMixin):
    """
    User class for BlenderID, implementing a fully featured User model with
    admin-compliant permissions.

    Email and password are required. Other fields are optional.
    """
    email = models.EmailField(
        _('email address'),
        max_length=64,
        unique=True,
        help_text=_('Required. 64 characters or fewer.'),
        error_messages={
            'unique': _("A user with that email address already exists."),
        },
        db_index=True,
    )
    full_name = models.CharField(_('full name'), max_length=80, blank=True, db_index=True)

    # Named 'nickname' and not 'username', because the latter already is a
    # 'thing' in Django. Not having one, and identifying users by their email
    # address, was our own customisation.
    # Bringing back a field 'username' with different semantics would be
    # confusing. For example, there still is a field 'username' in the default
    # Django auth form that is used for 'the thing used to log in', which is
    # the email address in our case.
    nickname = models.CharField(
        'nickname',
        max_length=80,
        unique=True,
        help_text=_('A short (one-word) name that can be used to address you. '
                    '80 characters or fewer. Letters, digits, and ./+/-/_ only.'),
        validators=[UnicodeNicknameValidator()],
        error_messages={
            'unique': _("That name is already used by someone else."),
        },
    )

    roles = models.ManyToManyField('Role', related_name='users', blank=True)
    public_roles_as_string = models.CharField(
        'Public roles as string',
        max_length=255,
        blank=True,
        default='',
        help_text=_('String representation of public roles, for comparison in webhooks'))

    confirmed_email_at = models.DateTimeField(
        null=True, blank=True,
        help_text=_('Designates the date & time at which the user confirmed their email address. '
                    'None if not yet confirmed.'))
    last_login_ip = models.GenericIPAddressField(
        null=True, blank=True,
        help_text=_('IP address (IPv4 or IPv6) used for previous login, if any.'))
    current_login_ip = models.GenericIPAddressField(
        null=True, blank=True,
        help_text=_('IP address (IPv4 or IPv6) used for current login, if any.'))
    login_count = models.PositiveIntegerField(
        default=0, blank=True,
        help_text=_('Number of times this user logged in.'))

    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    last_update = models.DateTimeField(_('last update'), default=timezone.now)
    privacy_policy_agreed = models.DateTimeField(
        _('privacy policy agreed'), null=True,
        help_text=_('Date when this user agreed to our privacy policy.'))

    email_change_preconfirm = models.EmailField(
        _('email address to change to'),
        blank=True,
        max_length=64,
        help_text=_('New address for the user, set while in the confirmation flow.'),
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __repr__(self) -> str:
        return f'<User id={self.id} email={self.email!r}>'

    def save(self, *args, **kwargs):
        self.last_update = timezone.now()
        updated_fields = {'last_update'}

        if kwargs.get('update_fields') is not None:
            kwargs['update_fields'] = set(kwargs['update_fields']).union(updated_fields)

        return super().save(*args, **kwargs)

    def public_roles(self) -> set:
        """Returns public role names.

        Used in the bid_api.signals module to detect role changes without
        using more lookups in the database.
        """
        return {role.name
                for role in self.roles.filter(is_public=True, is_active=True)}

    def public_badges(self) -> models.query.QuerySet:
        """Returns a QuerySet of public badges."""
        return self.roles.filter(is_public=True, is_active=True, is_badge=True)

    def get_full_name(self):
        """
        Returns the full name.
        """
        return self.full_name.strip()

    def get_short_name(self):
        """Returns the short name for the user."""
        parts = self.full_name.split(' ', 1)
        return parts[0]

    def email_user(self, subject, message, from_email=None, **kwargs):
        """
        Sends an email to this User.
        """
        send_mail(subject, message, from_email, [self.email], **kwargs)

    @property
    def has_confirmed_email(self):
        return self.confirmed_email_at is not None

    @property
    def email_to_confirm(self):
        """The email to confirm, either 'email_change_preconfirm' when set, or 'email'."""
        return self.email_change_preconfirm or self.email

    @property
    def role_names(self) -> typing.Set[str]:
        return {role.name for role in self.roles.all()}

    @property
    def must_pp_agree(self) -> bool:
        """Return True when user needs to agree to new privacy policy."""
        return self.privacy_policy_agreed is None or self.privacy_policy_agreed < settings.PPDATE


class SettingValueField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 128
        super().__init__(*args, **kwargs)


SETTING_DATA_TYPE_CHOICES = [
    ('bool', 'Boolean'),
]


class Setting(models.Model):
    name = models.CharField(max_length=128)
    description = models.CharField(max_length=128)
    data_type = models.CharField(max_length=32, choices=SETTING_DATA_TYPE_CHOICES, default='bool')
    default = SettingValueField()
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, through='UserSetting')

    def __str__(self):
        return self.name.replace('_', ' ').title()


class UserSetting(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    setting = models.ForeignKey(Setting, on_delete=models.CASCADE)
    unconstrained_value = SettingValueField()

    def __str__(self):
        return 'Setting %r of %r' % (self.setting.name, self.user.email)


class Role(models.Model):
    name = models.CharField(max_length=80)
    description = models.CharField(
        max_length=255, blank=True, null=False,
        help_text="Note that this is shown for badges on users' dashboard page.")
    is_active = models.BooleanField(default=True, null=False)
    is_badge = models.BooleanField(default=False, null=False)
    is_public = models.BooleanField(
        default=True, null=False,
        help_text='When enabled, this role/badge will be readable through the userinfo API.')

    may_manage_roles = models.ManyToManyField(
        'Role', related_name='managers', blank=True,
        help_text='Users with this role will be able to grant or revoke these roles to '
                  'any other user.')

    # For Badges:
    label = models.CharField(
        max_length=255, blank=True, null=False,
        help_text='Human-readable name for a badge. Required for badges, not for roles.')
    badge_img = models.ImageField(
        help_text='Visual representation of a badge.',
        upload_to='badges',
        height_field='badge_img_height',
        width_field='badge_img_width',
        null=True, blank=True)
    badge_img_height = models.IntegerField(null=True, blank=True)
    badge_img_width = models.IntegerField(null=True, blank=True)
    link = models.URLField(null=True, blank=True,
                           help_text='Clicking on a badge image will lead to this link.')

    class Meta:
        ordering = ['-is_active', 'name']

    def __str__(self):
        if self.is_active:
            return self.name
        return '%s [inactive]' % self.name

    @property
    def admin_url(self) -> str:
        view_name = f"admin:{self._meta.app_label}_{self._meta.model_name}_change"
        return urlresolvers.reverse(view_name, args=(self.id,))

    def clean(self):
        # Labels are required for badges.
        if self.is_badge and not self.label:
            raise ValidationError({'label': _('Badges must have a label.')})


class OAuth2AccessToken(oa2_models.AbstractAccessToken):
    class Meta:
        verbose_name = 'OAuth2 access token'

    host_label = models.CharField(max_length=255, unique=False, blank=True)
    subclient = models.CharField(max_length=255, unique=False, blank=True)


class OAuth2RefreshToken(oa2_models.AbstractRefreshToken):
    class Meta:
        verbose_name = 'OAuth2 refresh token'


class OAuth2Application(oa2_models.AbstractApplication):
    class Meta:
        verbose_name = 'OAuth2 application'

    url = models.URLField(
        unique=False, blank=True,
        help_text="URL to display on 'access' page for users.")
    notes = models.TextField(
        blank=True,
        help_text='Information about this application, for staff only, not to present on frontend.')


class UserNote(models.Model):
    """CRM-like note added to a user."""
    class Meta:
        verbose_name = 'Note'
        ordering = ('-created', )

    user = models.ForeignKey(User, related_name='notes', on_delete=models.CASCADE)
    creator = models.ForeignKey(User,
                                null=True,
                                blank=True,
                                related_name='created_notes',
                                on_delete=models.PROTECT,
                                limit_choices_to={'is_staff': True})
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    note = models.TextField(blank=False)

    def __str__(self):
        return 'Note'
