"""Mix-in classes for views."""
import logging
import urllib.parse

from django.urls import reverse_lazy

log = logging.getLogger(__name__)


class PageIdMixin:
    page_id = ''

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_id'] = self.page_id
        return ctx


class RedirectToPrivacyAgreeMixin:
    privacy_policy_agree_url = reverse_lazy('bid_main:privacy_policy_agree')

    def get_success_url(self):
        """Return the user-originating redirect URL if it's safe."""

        regular_redir_url = super().get_success_url()
        if not self.request.user.must_pp_agree:
            return regular_redir_url

        # User must agree to privacy policy first before being redirected.
        next_url_qs = urllib.parse.urlencode({
            'next': regular_redir_url,
        })
        redirect_to = f'{self.privacy_policy_agree_url}?{next_url_qs}'
        log.debug('Directing user to %s', redirect_to)
        return redirect_to
