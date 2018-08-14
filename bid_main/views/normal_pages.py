"""Normal stuff, like index, profile editing, etc.

No error handlers, no usually-one-off things like registration and
email confirmation.
"""

import logging

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import views as auth_views
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView, FormView
from django.views.generic.edit import UpdateView
import loginas.utils
import oauth2_provider.models as oauth2_models

from .. import forms
from ..models import User
from . import mixins

log = logging.getLogger(__name__)


class IndexView(LoginRequiredMixin, mixins.PageIdMixin, TemplateView):
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
        user = self.request.user
        role_names = user.role_names

        # Figure out which Blender ID 'apps' the user has access to.
        # Currently this is just based on a hard-coded set of roles.
        apps = {name for name, roles in self.BID_APP_TO_ROLES.items()
                if roles.intersection(role_names)}
        ctx['apps'] = apps

        ctx['cloud_needs_renewal'] = ('cloud_has_subscription' in role_names and
                                      'cloud_subscriber' not in role_names)
        ctx['show_confirm_address'] = not user.has_confirmed_email
        return ctx


class LoginView(mixins.RedirectToPrivacyAgreeMixin, mixins.PageIdMixin, auth_views.LoginView):
    """Shows the login view."""

    page_id = 'login'
    template_name = 'bid_main/login.html'
    authentication_form = forms.AuthenticationForm
    redirect_authenticated_user = True
    success_url_allowed_hosts = settings.NEXT_REDIR_AFTER_LOGIN_ALLOWED_HOSTS

    @method_decorator(sensitive_post_parameters())
    @method_decorator(csrf_exempt)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        """Don't check CSRF token when already authenticated."""
        if self.redirect_authenticated_user and self.request.user.is_authenticated:
            redirect_to = self.get_success_url()
            if redirect_to == self.request.path:
                raise ValueError(
                    "Redirection loop for authenticated user detected. Check that "
                    "your LOGIN_REDIRECT_URL doesn't point to a login page."
                )
            return HttpResponseRedirect(redirect_to)
        return super().dispatch(request, *args, **kwargs)


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


class AboutView(mixins.PageIdMixin, TemplateView):
    page_id = 'about'
    template_name = 'bid_main/about.html'

    def dispatch(self, request, *args, **kwargs):
        """Redirect to the login page, but without specifying 'next' param."""

        if request.user.is_anonymous:
            redirect_to = reverse_lazy('bid_main:login')
            return HttpResponseRedirect(redirect_to)
        return super().dispatch(request, *args, **kwargs)


class ProfileView(LoginRequiredMixin, UpdateView):
    form_class = forms.UserProfileForm
    model = User
    template_name = 'bid_main/profile.html'
    success_url = reverse_lazy('bid_main:index')
    confirm_url = reverse_lazy('bid_main:confirm-email-change')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        """Redirect to success URL or to the confirm-email flow."""
        success_resp = super().form_valid(form)  # this also saves form.instance
        if form.instance.email_change_preconfirm:
            return HttpResponseRedirect(self.confirm_url)
        return success_resp


class SwitchUserView(mixins.RedirectToPrivacyAgreeMixin, LoginRequiredMixin, auth_views.LoginView):
    template_name = 'bid_main/switch_user.html'
    form_class = forms.AuthenticationForm
    success_url_allowed_hosts = settings.NEXT_REDIR_AFTER_LOGIN_ALLOWED_HOSTS

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['next'] = self.request.GET.get('next', '')
        return ctx

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        switch_to = self.kwargs.get('switch_to')
        if switch_to:
            kwargs['initial'] = {**kwargs.get('initial', {}),
                                 'username': switch_to}
        return kwargs


class ApplicationTokenView(mixins.PageIdMixin, LoginRequiredMixin, FormView):
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


class PrivacyPolicyAgreeView(mixins.PageIdMixin, LoginRequiredMixin, FormView):
    page_id = 'privacy_policy_agree'
    template_name = 'bid_main/privacy_policy_agree.html'
    form_class = forms.PrivacyPolicyAgreeForm
    default_success_url = reverse_lazy('bid_main:index')

    log = logging.getLogger(f'{__name__}.ApplicationTokenView')

    def get_initial(self) -> dict:
        next_url = self.request.GET.get('next') or self.default_success_url
        return {'next_url': next_url}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['may_skip'] = self.request.GET.get('mayskip', '') == 'yes'
        return ctx

    def form_valid(self, form):
        """Save the agreement and redirect."""
        from django.contrib.contenttypes.models import ContentType
        from django.contrib.admin.models import LogEntry, ADDITION

        now = timezone.now()
        self.request.user.privacy_policy_agreed = now
        log.info('User agreed to privacy policy at %s', now)
        self.request.user.save(update_fields=('privacy_policy_agreed',))

        LogEntry.objects.log_action(
            user_id=self.request.user.id,
            content_type_id=ContentType.objects.get_for_model(User).pk,
            object_id=self.request.user.id,
            object_repr=str(self.request.user),
            action_flag=ADDITION,
            change_message=f'Agreed to privacy policy dated {settings.PPDATE}')

        next_url = form.cleaned_data['next_url'] or self.default_success_url
        return HttpResponseRedirect(next_url)
