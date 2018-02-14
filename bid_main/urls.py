from django.conf import settings
from django.conf.urls import url
from django.urls import reverse_lazy
from django.contrib.auth import views as auth_views

from . import views, forms

urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^settings/profile$', views.ProfileView.as_view(), name='profile'),
    url(r'^login$', views.LoginView.as_view(), name='login'),
    url(r'^about$', views.AboutView.as_view(), name='about'),
    url(r'^logout$', views.LogoutView.as_view(next_page='bid_main:about'), name='logout'),
    url(r'^switch/(?P<switch_to>.+)?$', views.SwitchUserView.as_view(), name='switch_user'),
    url(r'^applications', views.ApplicationTokenView.as_view(), name='auth_tokens'),

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
    url(r'^register/$', views.RegistrationView.as_view(), name='register'),
    url(r'^register/signed-up/$',
        auth_views.PasswordResetDoneView.as_view(
            template_name='registration/initial_signed_up.html'),
        name='register-done'),
    url(
        r'^register/password/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        auth_views.password_reset_confirm, {
            'template_name': 'registration/initial_set_password.html',
            'post_reset_redirect': 'bid_main:register-complete',
            'set_password_form': forms.SetInitialPasswordForm,
        }, name='register-confirm'),
    url(r'^register/complete/$', auth_views.password_reset_complete, {
        'template_name': 'registration/registration_complete.html',
    }, name='register-complete'),

    url(r'^confirm-email/start$', views.ConfirmEmailView.as_view(), name='confirm-email'),
    url(r'^confirm-email/start-change$', views.ConfirmEmailView.as_view(
        template_name='bid_main/confirm_email/change.html'), name='confirm-email-change'),
    url(r'^confirm-email/cancel-change$', views.CancelEmailChangeView.as_view(),
        name='cancel-email-change'),
    url(r'^confirm-email/sent$', views.ConfirmEmailSentView.as_view(), name='confirm-email-sent'),
    url(r'^confirm-email/verified/(?P<info>[^/]+)/(?P<hmac>[^/]+)$',
        views.ConfirmEmailVerifiedView.as_view(),
        name='confirm-email-verified'),
    url(r'^confirm-email/poll$', views.ConfirmEmailPollView.as_view(), name='confirm-email-poll'),
]

# Only enable this on a dev server:
if settings.DEBUG:
    urlpatterns += [
        url(r'^debug/email-changed$', views.test_mail_email_changed),
        url(r'^debug/email-verify$', views.test_mail_verify_address),
        url(r'^error/(?P<code>\d+)$', views.test_error),
    ]
