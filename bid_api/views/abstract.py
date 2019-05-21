import logging
import typing
import urllib.parse

from django.contrib.sites.models import Site
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.views.generic import View

log = logging.getLogger(__name__)


class AbstractAPIView(View):
    """Excempted from CSRF requests and never cached."""

    @method_decorator(csrf_exempt)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def make_absolute(self, request, relative_url: str) -> str:
        """Turns the host-relative URL into an absolute one."""

        current_site = Site.objects.get_current()
        return urllib.parse.urljoin(f'{request.scheme}://{current_site.domain}/', relative_url)

    def check_user_id(self, request, user_id_from_url: str) -> typing.Optional[JsonResponse]:
        """Check whether the user ID owns the authentication token.

        :return: tuple (uid, err), where uid is the integer user ID, and err is
            a JSON response with an error message, or None if all is ok.
        """

        request_user = getattr(request, 'user', None)
        if request_user is None or str(request.user.id) != user_id_from_url:
            my_log = getattr(self, 'log', log)
            my_log.warning('Request from %s on %s for user %s did not match auth token owner %s',
                           request.META.get('REMOTE_ADDR', '-unknown-'),
                           request.path,
                           user_id_from_url,
                           request.user.id)

            return JsonResponse(
                {'message': 'user ID on URL did not match authentication token owner'},
                status=403)
        return None
