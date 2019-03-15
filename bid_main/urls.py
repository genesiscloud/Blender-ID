from django.conf import settings
from django.conf.urls import url
from django.urls import reverse_lazy
from django.contrib.auth import views as auth_views

from . import forms
from .views import normal_pages, registration_email, json_api

app_name = 'bid_main'
urlpatterns = [
    url(r'^$', normal_pages.IndexView.as_view(), name='index'),
    url(r'^settings/profile$', normal_pages.ProfileView.as_view(), name='profile'),
    url(r'^login$', normal_pages.LoginView.as_view(), name='login'),
    url(r'^about$', normal_pages.AboutView.as_view(), name='about'),
    url(r'^logout$', normal_pages.LogoutView.as_view(next_page='bid_main:about'), name='logout'),
    url(r'^switch/?$', normal_pages.SwitchUserView.as_view(), name='switch_user'),
    url(r'^switch/(?P<switch_to>.+)$', normal_pages.SwitchUserView.as_view(), name='switch_user'),
    url(r'^applications', normal_pages.ApplicationTokenView.as_view(), name='auth_tokens'),
    url(r'^privacy-policy/agree$', normal_pages.PrivacyPolicyAgreeView.as_view(),
        name='privacy_policy_agree'),

    url(r'^badge-toggle-private', json_api.BadgeTogglePrivateView.as_view(),
        name='badge_toggle_private'),

    url('^change$',
        auth_views.PasswordChangeView.as_view(
            form_class=forms.PasswordChangeForm,
            success_url=reverse_lazy('bid_main:password_change_done')),
        name='password_change'),
    url('^change-password/done$', auth_views.PasswordChangeDoneView.as_view(),
        name='password_change_done'),

    url(r'^password_reset/$',
        auth_views.PasswordResetView.as_view(
            form_class=forms.PasswordResetForm,
            success_url=reverse_lazy('bid_main:password_reset_done')),
        name='password_reset'),
    url(r'^password_reset/done/$',
        auth_views.PasswordResetDoneView.as_view(),
        name='password_reset_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        auth_views.PasswordResetConfirmView.as_view(
            success_url=reverse_lazy('bid_main:password_reset_complete')),
        name='password_reset_confirm'),
    url(r'^password_reset/complete/$',
        auth_views.PasswordResetCompleteView.as_view(),
        name='password_reset_complete'),

    # Source of registration machinery:
    # http://musings.tinbrain.net/blog/2014/sep/21/registration-django-easy-way/
    url(r'^register/$', registration_email.RegistrationView.as_view(), name='register'),
    url(r'^register/signed-up/$',
        auth_views.PasswordResetDoneView.as_view(
            template_name='registration/initial_signed_up.html'),
        name='register-done'),
    url(
        r'^register/password/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        registration_email.InitialSetPasswordView.as_view(), name='register-confirm'),
    url(r'^register/complete/$', auth_views.PasswordResetCompleteView.as_view(), {
        'template_name': 'registration/registration_complete.html',
    }, name='register-complete'),

    url(r'^confirm-email/start$',
        registration_email.ConfirmEmailView.as_view(),
        name='confirm-email'),
    url(r'^confirm-email/start-change$', registration_email.ConfirmEmailView.as_view(
        template_name='bid_main/confirm_email/change.html'), name='confirm-email-change'),
    url(r'^confirm-email/cancel-change$', registration_email.CancelEmailChangeView.as_view(),
        name='cancel-email-change'),
    url(r'^confirm-email/sent$',
        registration_email.ConfirmEmailSentView.as_view(),
        name='confirm-email-sent'),
    url(r'^confirm-email/verified/(?P<info>[^/]+)/(?P<hmac>[^/]+)$',
        registration_email.ConfirmEmailVerifiedView.as_view(),
        name='confirm-email-verified'),
    url(r'^confirm-email/poll$',
        registration_email.ConfirmEmailPollView.as_view(),
        name='confirm-email-poll'),
]

# Only enable this on a dev server:
if settings.DEBUG:
    from .views import testviews

    urlpatterns += [
        url(r'^debug/email-changed$', testviews.test_mail_email_changed),
        url(r'^debug/email-verify$', testviews.test_mail_verify_address),
        url(r'^error/(?P<code>\d+)$', testviews.test_error),
    ]
