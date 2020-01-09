import urllib.parse

from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from . import models
from .admin_decorators import short_description

# Configure the admin site. Easier than creating our own AdminSite subclass.
# Text to put at the end of each page's <title>.
admin.site.site_title = 'Blender-ID admin'
# Text to put in each page's <h1>.
admin.site.site_header = 'Blender-ID Administration'


class UserSettingInline(admin.TabularInline):
    model = models.UserSetting
    extra = 0
    classes = ['collapse']


class UserNotesInline(admin.TabularInline):
    model = models.UserNote
    fk_name = 'user'
    extra = 0
    readonly_fields = ('creator', 'created')
    fields = ('creator', 'created', 'note')


def _add_change_log(queryset, request, change_message: str):
    cur_user_id = request.user.id
    content_type_id = ContentType.objects.get_for_model(models.User).pk

    for target_user in queryset:
        LogEntry.objects.log_action(
            user_id=cur_user_id,
            content_type_id=content_type_id,
            object_id=target_user.id,
            object_repr=str(target_user),
            action_flag=CHANGE,
            change_message=change_message)


@short_description('Make selected users staff')
def make_staff(modeladmin, request, queryset):
    queryset.update(is_staff=True)
    _add_change_log(queryset, request, 'Granted staff status')


@short_description('Make selected users non-staff')
def unmake_staff(modeladmin, request, queryset):
    queryset.update(is_staff=False)
    _add_change_log(queryset, request, 'Revoked staff status')


@short_description('Activate selected users')
def activate(modeladmin, request, queryset):
    queryset.update(is_active=True)
    _add_change_log(queryset, request, 'Activated user')


@short_description('Deactivate selected users')
def deactivate(modeladmin, request, queryset):
    queryset.update(is_active=False)
    _add_change_log(queryset, request, 'Deactivated user')


@short_description('Request deletion of selected users')
def request_deletion(modeladmin, request, queryset):
    matched_count: int = queryset.update(deletion_requested=True)
    _add_change_log(queryset, request, "Marked user as 'deletion requested'")
    modeladmin.message_user(request, f'{matched_count} users marked for deletion',
                            level=messages.WARNING)


@short_description('Send address confirmation mails to selected users')
def send_confirm_mails(modeladmin, request, queryset):
    from .email import send_verify_address

    mailed = {
        True: set(),
        False: set(),
    }
    for user in queryset:
        ok = send_verify_address(user, request.scheme)
        mailed[ok].add(user.email)
        if ok:
            _add_change_log((user,), request, "Sent 'confirm email address' mail")
        else:
            _add_change_log((user,), request,
                            "Tried to send 'confirm email address' mail, which failed")

    mailed_ok = ', '.join(sorted(mailed[True])) or 'nobody'
    mailed_fail = ', '.join(sorted(mailed[False]))

    if mailed[False]:
        level = messages.WARNING
        msg = f'Sent mail to {mailed_ok}; mail to {mailed_fail} failed.'
    else:
        level = messages.INFO
        msg = f'Sent mail to {mailed_ok}.'
    modeladmin.message_user(request, msg, level=level)


@admin.register(models.User)
class UserAdmin(BaseUserAdmin):
    inlines = (UserSettingInline, UserNotesInline)

    fieldsets = (
        (None, {'fields': ('email',
                           'nickname',
                           'deletion_requested',
                           'avatar',
                           'email_change_preconfirm',
                           'password',
                           'full_name',
                           'roles', 'private_badges')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser',
                       'groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
        (_('Important dates'), {
            'fields': ('date_joined', 'last_update', 'confirmed_email_at', 'privacy_policy_agreed'),
            'classes': ('collapse',),
        }),
        (_('Login info'), {
            'fields': ('last_login', 'last_login_ip', 'current_login_ip', 'login_count'),
            'classes': ('collapse',),
        }),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'nickname'),
        }),
    )

    list_display = ('email', 'full_name', 'is_active', 'is_staff', 'deletion_requested',
                    'role_names', 'last_update', 'confirmed_email_at', 'links')
    list_display_links = ('email', 'full_name')
    list_filter = ('roles', 'is_active', 'deletion_requested', 'groups',
                   'confirmed_email_at', 'is_staff', 'is_superuser',
                   'date_joined', 'privacy_policy_agreed')
    list_per_page = 12
    search_fields = ('email', 'full_name', 'email_change_preconfirm', 'nickname')
    ordering = ('-last_update',)
    readonly_fields = ('deletion_requested',)

    actions = [request_deletion, activate, deactivate, make_staff, unmake_staff, send_confirm_mails]

    def role_names(self, user):
        """Lists role names of the user.

        Can be used in list_display, but makes things slow.
        """
        roles = user.roles.filter(is_active=True)
        if not roles:
            return '-'
        suffix = ''
        if len(roles) > 3:
            suffix = ', … and %i more…' % (len(roles) - 3)
            roles = roles[:3]
        return ', '.join(g.name for g in roles) + suffix

    @staticmethod
    def links(user) -> str:
        """Links to Store & Cloud."""
        template = (
            '<a title="Store" href="https://store.blender.org/wp-admin/users.php?s={}">S</a>&nbsp;'
            '<a title="Cloud" href="https://cloud.blender.org/u/?q={}&page=0">C</a>&nbsp;'
            '<a title="Fund" href="https://fund.blender.org/admin/auth/user/?q={}">F</a>&nbsp;'
            '<a title="Open Data" href="https://opendata.blender.org/admin/auth/user/?q={}">MD</a>'
        )
        email = urllib.parse.quote(user.email)
        return format_html(template, email, email, email, email)

    def save_formset(self, request, form, formset, change):
        """Sets the note.creator for new notes to the current user."""
        if not issubclass(formset.model, models.UserNote):
            return super().save_formset(request, form, formset, change)

        changed_notes = formset.save()
        for note in changed_notes:
            if note.creator is not None:
                continue
            note.creator = request.user
            note.save()
        return changed_notes


@admin.register(models.Setting)
class SettingAdmin(admin.ModelAdmin):
    model = models.Setting

    list_display = ('name', 'description', 'data_type', 'default')
    list_filter = ('data_type',)
    search_fields = ('name', 'description')


@short_description('Mark selected roles as badges')
def make_badge(modeladmin, request, queryset):
    queryset.update(is_badge=True)


@short_description('Un-mark selected roles as badges')
def make_not_badge(modeladmin, request, queryset):
    queryset.update(is_badge=False)


@short_description('Mark selected roles as active')
def make_active(modeladmin, request, queryset):
    queryset.update(is_active=True)


@short_description('Mark selected roles as inactive')
def make_inactive(modeladmin, request, queryset):
    queryset.update(is_active=False)


@admin.register(models.Role)
class RoleAdmin(admin.ModelAdmin):
    model = models.Role

    list_display = ('name', 'label', 'description', 'is_badge', 'is_public', 'is_active',
                    'badge_img')
    list_filter = ('is_badge', 'is_public', 'is_active')
    search_fields = ('name', 'description', 'label')

    actions = [make_badge, make_not_badge, make_active, make_inactive]

    fieldsets = (
        (None, {'fields': ('name', 'description', 'is_public', 'is_active',
                           'may_manage_roles')}),
        (_('Badges'), {
            'fields': ('is_badge', 'label', 'badge_img', 'link'),
        }),
    )


# Erase the oauth_provider admin classes so that we can register our own.
# Butt ugly but it seems to work.
try:
    admin.site.unregister(models.OAuth2AccessToken)
except admin.site.NotRegistered:
    pass


@admin.register(models.OAuth2AccessToken)
class AccessTokenAdmin(admin.ModelAdmin):
    list_display = ('token', 'user', 'application', 'scope', 'expires')
    list_filter = ('application', 'scope')
    raw_id_fields = ('user', 'source_refresh_token')
    search_fields = ('scope',)
