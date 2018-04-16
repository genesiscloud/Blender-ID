import logging

from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.utils.decorators import method_decorator
from oauth2_provider.decorators import protected_resource

from .abstract import AbstractAPIView

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
            return HttpResponseBadRequest('invalid user ID')

        log.debug('Fetching user %d on behalf of API user %s', uid, request.user)
        try:
            user = UserModel.objects.get(id=uid)
        except UserModel.DoesNotExist:
            return HttpResponseNotFound('user not found')

        return user_info_response(user)


class StatsView(AbstractAPIView):
    """Returns aggregate statistics.

    This does require the OAuth token to have userstats scope.
    """

    def get(self, request):
        obs = UserModel.objects
        stats = {
            'users': {
                'unconfirmed': obs.filter(confirmed_email_at__isnull=True).count(),
                'confirmed': obs.filter(confirmed_email_at__isnull=False).count(),
                'total': obs.count(),
            }
        }

        return JsonResponse(stats)
