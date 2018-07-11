import urllib.parse

from django.contrib.sites.models import Site
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.views.generic import View


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
