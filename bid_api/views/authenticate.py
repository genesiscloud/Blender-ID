import logging

from django.contrib.auth import get_user_model, authenticate
from django import http
from django.utils.decorators import method_decorator
from oauth2_provider.decorators import protected_resource

from .abstract import AbstractAPIView

UserModel = get_user_model()


class AuthenticateView(AbstractAPIView):
    """Authentication of users for external systems.

    This API endpoint allows an external system to validate an email + password
    against our user database. The external system MUST authenticate itself
    with a bearer token that has the 'authenticate' scope.

    Since the external system is supposed to be trusted, we return extra
    failure information; a 403 response will indicate whether the password
    was invalid or the user doesn't exist at all. This allows the external
    system to gracefully fall back to local authentication when we cannot
    authenticate the user.
    """
    log = logging.getLogger(f'{__name__}.AuthenticateView')

    @method_decorator(protected_resource(scopes=['authenticate']))
    def post(self, request) -> http.HttpResponse:
        try:
            email = request.POST['email']
            password = request.POST['password']
        except KeyError as ex:
            self.log.warning('missing form key (%s) when authenticating on behalf of %s',
                             ex, request.user)
            return http.HttpResponseBadRequest()
        self.log.debug('checking login of user %r on behalf of %s',
                       email, request.user)

        # If we use the actual request object, Django will see that it was
        # already authenticated via OAuth, and immediately return. With a
        # fresh request object Django will actually check these credentials.
        fake_request = http.HttpRequest()
        db_user = authenticate(fake_request, username=email, password=password)
        if not db_user:
            # See whether a user with this email account actually exists at all.
            if len(UserModel.objects.filter(email=email)):
                error = 'bad-pw'
            else:
                error = 'no-such-account'

            self.log.debug('invalid login (%s) of user %r on behalf of %s',
                           error, email, request.user)

            return http.JsonResponse({
                'error': error
            }, content_type='application/json', status=403)

        return http.JsonResponse({
            'user_id': db_user.id,
            'email': db_user.email,
            'full_name': db_user.full_name,
        }, status=200)
