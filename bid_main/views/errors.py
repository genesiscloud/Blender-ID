"""Error handlers."""

from django.http import HttpResponse
from django.views.generic import TemplateView


class ErrorView(TemplateView):
    """Renders an error page."""
    # TODO(Sybren): respond as JSON when this is an XHR.

    status = 500

    def dispatch(self, request=None, *args, **kwargs):
        if request is None or request.method in {'HEAD', 'OPTIONS'}:
            # Don't render templates in this case.
            return HttpResponse(status=self.status)

        # We allow any method for this view,
        response = self.render_to_response(self.get_context_data(**kwargs))
        response.status_code = self.status
        return response


def csrf_failure(request, reason=""):
    import django.views.csrf

    return django.views.csrf.csrf_failure(request,
                                          reason=reason,
                                          template_name='errors/403_csrf.html')
