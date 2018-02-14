from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
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


@short_description('Make selected users staff')
def make_staff(modeladmin, request, queryset):
    queryset.update(is_staff=True)


@short_description('Make selected users non-staff')
def unmake_staff(modeladmin, request, queryset):
    queryset.update(is_staff=False)


@short_description('Send address confirmation mails to selected users')
def send_confirm_mails(modeladmin, request, queryset):
    from django.contrib import messages
    from .email import send_verify_address

    mailed = {
        True: set(),
        False: set(),
    }
    for user in queryset:
        ok = send_verify_address(user, request.scheme)
        mailed[ok].add(user.email)

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
        (None, {'fields': ('email', 'email_change_preconfirm', 'password', 'full_name', 'roles')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser',
                       'groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
        (_('Important dates'), {
            'fields': ('date_joined', 'last_update', 'confirmed_email_at'),
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
            'fields': ('email', 'password1', 'password2'),
        }),
    )

    list_display = ('email', 'full_name', 'is_active', 'is_staff', 'role_names', 'last_update',
                    'confirmed_email_at')
    list_display_links = ('email', 'full_name')
    list_filter = ('roles', 'is_active', 'groups',
                   'confirmed_email_at', 'is_staff', 'is_superuser')
    list_per_page = 12
    search_fields = ('email', 'full_name')
    ordering = ('-last_update',)

    actions = [make_staff, unmake_staff, send_confirm_mails]

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

    list_display = ('name', 'description', 'is_badge', 'is_public', 'is_active')
    list_filter = ('is_badge', 'is_public', 'is_active')
    search_fields = ('name', 'description')

    actions = [make_badge, make_not_badge, make_active, make_inactive]


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
    raw_id_fields = ('user',)
    search_fields = ('scope',)
