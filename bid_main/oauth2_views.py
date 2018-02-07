"""Our own hooks into the OAuth2 flow."""

import logging

from django.shortcuts import render
from oauth2_provider import views as base_views
from oauth2_provider.models import get_application_model

from . import forms

log = logging.getLogger(__name__)
OAuth2Application = get_application_model()


class AuthorizationView(base_views.AuthorizationView):
    """Refuses to authorize user with unconfirmed email."""

    log = log.getChild('AuthorizationView')

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.has_confirmed_email:
            return self.force_email_confirm(request)
        return super().get(request, *args, **kwargs)

    def force_email_confirm(self, request):
        """Disrupt the OAuth2 flow by forcing the user to confirm their email."""

        # This copies some stuff from the superclass to figure out the OAuth2 application.
        _, credentials = self.validate_authorization_request(request)
        application = OAuth2Application.objects.get(client_id=credentials["client_id"])

        self.log.info('Forcing user to confirm email before allowing OAuth2 flow with app %r.',
                      application.name)

        qs = request.META.get('QUERY_STRING', '')
        requested = f'{request.path}?{qs}' if qs else request.path
        self.log.debug('Their original URL was %r', requested)

        ctx = {
            'form': forms.ConfirmEmailStartForm(
                {'next_url': requested,
                 'next_name': application.name}),
            'next_name': application.name,
            'user': request.user,
        }
        return render(request, 'bid_main/confirm_email/start_for_oauth.html', ctx)
