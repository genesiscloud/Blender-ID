import logging

from django.db import transaction
from django.db.models import Count
from django.conf import settings
from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import CreateView, TemplateView, FormView
from django.views.generic.edit import UpdateView

import oauth2_provider.models as oauth2_models
import loginas.utils

from . import forms
from .models import User


class PageIdMixin:
    page_id = ''

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_id'] = self.page_id
        return ctx


class IndexView(LoginRequiredMixin, PageIdMixin, TemplateView):
    page_id = 'index'
    template_name = 'bid_main/index.html'
    login_url = reverse_lazy('bid_main:login')
    redirect_field_name = None

    # Anyone with any of those roles gets that app listed
    # on the index page.
    BID_APP_TO_ROLES = {
        'cloud': {'cloud_demo', 'cloud_has_subscription'},
        'network': {'network_member'},
        'bfct': {'bfct_trainer', 'bfct_board'},
    }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        role_names = self.request.user.role_names

        # Figure out which Blender ID 'apps' the user has access to.
        # Currently this is just based on a hard-coded set of roles.
        apps = {name for name, roles in self.BID_APP_TO_ROLES.items()
                if roles.intersection(role_names)}
        ctx['apps'] = apps

        ctx['cloud_needs_renewal'] = ('cloud_has_subscription' in role_names and
                                      'cloud_subscriber' not in role_names)

        return ctx


class LoginView(PageIdMixin, auth_views.LoginView):
    """Shows the login view."""

    page_id = 'login'
    template_name = 'bid_main/login.html'
    authentication_form = forms.AuthenticationForm


class LogoutView(auth_views.LogoutView):
    """Logout view with support for django-loginas.

    By default django-loginas registers the logout view at /admin/logout,
    which I don't like. I don't want to have /admin/ used by non-admin
    users.
    """

    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        loginas.utils.restore_original_login(request)

        next_page = self.get_next_page()
        if next_page:
            # Redirect to this page until the session has been cleared.
            return HttpResponseRedirect(next_page)
        return super(LogoutView, self).dispatch(request, *args, **kwargs)


class AboutView(PageIdMixin, TemplateView):
    page_id = 'about'
    template_name = 'bid_main/about.html'

    def dispatch(self, request, *args, **kwargs):
        """Redirect to the login page, but without specifying 'next' param."""

        if request.user.is_anonymous:
            redirect_to = reverse_lazy('bid_main:login')
            return HttpResponseRedirect(redirect_to)
        return super().dispatch(request, *args, **kwargs)


class RegistrationView(CreateView):
    form_class = forms.UserRegistrationForm
    model = User
    template_name_suffix = '_register_form'

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.set_password(User.objects.make_random_password())
        obj.save()

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
        # This form sends the email on save()
        reset_form.save(**opts)

        return redirect('bid_main:register-done')


class ProfileView(LoginRequiredMixin, UpdateView):
    form_class = forms.UserProfileForm
    model = User
    template_name = 'bid_main/profile.html'
    success_url = reverse_lazy('bid_main:index')

    def get_object(self, queryset=None):
        return self.request.user


class SwitchUserView(LoginRequiredMixin, auth_views.LoginView):
    template_name = 'bid_main/switch_user.html'
    form_class = forms.AuthenticationForm
    success_url_allowed_hosts = settings.NEXT_REDIR_AFTER_LOGIN_ALLOWED_HOSTS


def test_email_changed_mail(request):
    """View for designing the email without having to send it all the time."""
    from django.http import HttpResponse
    from .signals import construct_email_changed_mail

    email_body_html, *_ = construct_email_changed_mail(request.user, 'old@email.nl')

    return HttpResponse(email_body_html)


def test_error(request, code):
    from django.core import exceptions
    from django.http import response, Http404

    codes = {
        403: exceptions.PermissionDenied,
        404: Http404,
        500: exceptions.ImproperlyConfigured,
    }
    try:
        exc = codes[int(code)]
    except KeyError:
        return response.HttpResponse(f'error test for code {code}', status=int(code))
    else:
        raise exc(f'exception test for code {code}')


class ErrorView(TemplateView):
    """Renders an error page."""
    # TODO(Sybren): respond as JSON when this is an XHR.

    status = 500

    def dispatch(self, request, *args, **kwargs):
        from django.http.response import HttpResponse
        if request.method in {'HEAD', 'OPTIONS'}:
            # Don't render templates in this case.
            return HttpResponse(status=self.status)

        # We allow any method for this view,
        response = self.render_to_response(self.get_context_data(**kwargs))
        response.status_code = self.status
        return response


class ApplicationTokenView(PageIdMixin, LoginRequiredMixin, FormView):
    page_id = 'auth_tokens'
    template_name = 'bid_main/auth_tokens.html'
    form_class = forms.AppRevokeTokensForm
    success_url = reverse_lazy('bid_main:auth_tokens')

    log = logging.getLogger(f'{__name__}.ApplicationTokenView')

    def get(self, request, *args, **kwargs):
        ctx = self.get_context_data(**kwargs)

        tokens_per_app = list(request.user.bid_main_oauth2accesstoken
                              .values('application')
                              .annotate(Count('id'))
                              .order_by())
        app_ids = {tpa['application'] for tpa in tokens_per_app}
        app_model = oauth2_models.get_application_model()
        apps = app_model.objects.filter(id__in=app_ids).order_by('name')

        ctx['apps'] = apps

        return self.render_to_response(ctx)

    def form_valid(self, form):
        user = self.request.user
        app_id = form.cleaned_data['app_id']
        self.log.info('Revoking all oauth tokens for user %s, application %d', user, app_id)

        rt_model = oauth2_models.get_refresh_token_model()
        at_model = oauth2_models.get_access_token_model()
        gr_model = oauth2_models.get_grant_model()

        rt_model.objects.filter(user=user, application=app_id).delete()
        at_model.objects.filter(user=user, application=app_id).delete()
        gr_model.objects.filter(user=user, application=app_id).delete()

        return super().form_valid(form)


def csrf_failure(request, reason=""):
    import django.views.csrf

    return django.views.csrf.csrf_failure(request,
                                          reason=reason,
                                          template_name='errors/403_csrf.html')
