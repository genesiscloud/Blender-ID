"""JSON views that aren't real API calls.

Those are used by regular views, and contrary to real API calls (which would
live in bid_api) expect authentication via the sessions and CSRF checks rather
than via bearer tokens.
"""

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.generic import View

from .. import models

log = logging.getLogger(__name__)


class BadgeTogglePrivateView(LoginRequiredMixin, View):
    """JSON endpoint that toggles 'is_private' flag for badges."""

    def post(self, request, *args, **kwargs) -> JsonResponse:
        try:
            badge_name = request.POST['badge_name']
        except KeyError:
            return JsonResponse({'_message': 'no badge name given'}, status=422)

        role: models.Role = get_object_or_404(models.Role.objects, name=badge_name)
        if request.user.private_badges.filter(id=role.id).count():
            request.user.private_badges.remove(role)
            now_private = False
        else:
            request.user.private_badges.add(role)
            now_private = True

        return JsonResponse({'is_private': now_private})
