import logging
import typing

from django.contrib.auth import get_user_model
from django.http import (JsonResponse, HttpResponse, HttpResponseBadRequest, HttpResponseNotFound)
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from oauth2_provider.decorators import protected_resource

from .abstract import AbstractAPIView
from ..http_responses import HttpResponseNoContent
from bid_main.models import Role

log = logging.getLogger(__name__)
UserModel = get_user_model()


@protected_resource()
def user_info(request):
    """Returns JSON info about the current user."""

    return user_info_response(request.user)


def user_info_response(user: UserModel) -> JsonResponse:
    # This is returned as dict to be compatible with the old
    # Flask-based Blender ID implementation.
    public_roles = {role.name: True
                    for role in user.roles.filter(is_public=True)
                    if role.is_active}
    return JsonResponse({'id': user.id,
                         'full_name': user.get_full_name(),
                         'email': user.email,
                         'nickname': user.nickname,
                         'roles': public_roles})


class UserInfoView(AbstractAPIView):
    """Returns user info given a user ID.

    This does require the OAuth token to have userinfo scope.
    """

    @method_decorator(protected_resource(scopes=['userinfo']))
    def get(self, request, user_id):
        try:
            uid = int(user_id)
        except TypeError:
            # This is unlikely to happen as the URL only matches digits.
            return HttpResponseBadRequest('invalid user ID')

        log.debug('Fetching user %d on behalf of API user %s', uid, request.user)
        try:
            user = UserModel.objects.get(id=uid)
        except UserModel.DoesNotExist:
            return HttpResponseNotFound('user not found')

        return user_info_response(user)


class UserBadgeView(AbstractAPIView):
    """JSON badge info for a given user ID.

    It is only allowed to get the badge for the owner of the token.

    This does require the OAuth token to have badge scope.
    """

    @method_decorator(protected_resource(scopes=['badge']))
    def get(self, request, user_id) -> JsonResponse:
        err = self.check_user_id(request, user_id)
        if err is not None:
            return err

        log.debug('Fetching badges of user %s', request.user)
        badges = {
            role.name: self.badge_dict(request, role)
            for role in request.user.public_badges()
        }
        return JsonResponse({'user_id': request.user.id,
                             'badges': badges})

    def badge_dict(self, request, role):
        """Turns a Role into a dictionary for returning in the JSON response."""
        as_dict = {
            'label': role.label,
        }
        if role.link:
            as_dict['link'] = role.link
        if role.description:
            as_dict['description'] = role.description
        if role.badge_img:
            as_dict.update({
                'image': self.make_absolute(request, role.badge_img.url),
                'image_width': role.badge_img_width,
                'image_height': role.badge_img_height,
            })
        return as_dict


class BadgesHTMLView(AbstractAPIView):
    """Render HTML for a user's badges.

    The user is identified by the Bearer token used in the request.

    The Bearer token should have scope 'badge'.
    """
    sizes = {
        's': 64,
        'm': 128,
        'l': 256,
    }
    """Mapping from 'size' parameter to a size in pixels."""

    log = log.getChild('BadgesHTMLView')

    @method_decorator(protected_resource(scopes=['badge']))
    def get(self, request, user_id: str, size: str='s'):
        """Return HTML with the user's badges.

        Passing the user ID isn't strictly necessary. However, it does allow
        for caching the result (for a short while) based on the URL alone,
        and without having to cache the authentication token too.
        """

        err = self.check_user_id(request, user_id)
        if err is not None:
            return err

        badges: typing.Iterable[Role] = request.user.public_badges()
        if not badges:
            return HttpResponseNoContent()

        try:
            size_in_px = self.sizes[size]
        except KeyError:
            log.debug('Invalid badge size %r requested', size)
            resp = render(request, 'bid_api/badges/error_size_invalid.html',
                          {'requested_size': size, 'available_sizes': self.sizes})
            resp.status_code = 400
            return resp

        return render(request, 'bid_api/badges/user_badges.html',
                      {'badges': badges,
                       'size_string': f'{size_in_px}x{size_in_px}'})


class UserAvatarView(AbstractAPIView):
    """Avatar for this user.

    This is a public endpoint that redirects to the actual avatar thumbnail.
    """

    def get(self, request, user_id: str) -> HttpResponse:
        try:
            dbuser = UserModel.objects.get(id=int(user_id))
        except UserModel.DoesNotExist:
            return JsonResponse({'_message': 'user does not exist'}, status=404)
        return redirect(dbuser.avatar.thumbnail_url())


class StatsView(AbstractAPIView):
    """Return aggregate statistics."""

    def get(self, request):
        obs = UserModel.objects

        # Count how many people agreed to any privacy policy.
        pp_agreed = obs.filter(privacy_policy_agreed__isnull=False).count()

        # TODO(Sybren): update this when we introduce a new privacy policy;
        # in that case we need to compare to a newer date.
        pp_obsolete = 0

        total = obs.count()
        stats = {
            'users': {
                'unconfirmed': obs.filter(confirmed_email_at__isnull=True).count(),
                'confirmed': obs.filter(confirmed_email_at__isnull=False).count(),
                'privacy_policy_agreed': {
                    'latest': pp_agreed,
                    'obsolete': pp_obsolete,
                    'never': total - pp_agreed - pp_obsolete,
                },
                'total': total,
            }
        }

        return JsonResponse(stats)
