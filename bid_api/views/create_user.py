import logging

from django.db import transaction, IntegrityError
from django.contrib.auth import get_user_model
from django.contrib.admin.models import LogEntry, ADDITION
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse, HttpResponse
from django.utils.decorators import method_decorator
from django.forms import ModelForm
from oauth2_provider.decorators import protected_resource

from .abstract import AbstractAPIView

UserModel = get_user_model()


class CreateUserForm(ModelForm):
    """User creation form, using fields from UserModel."""

    class Meta:
        model = UserModel
        fields = ['email', 'full_name', 'password']


class CreateUserView(AbstractAPIView):
    """API endpoint for creating users.

    Requires an auth token with 'usercreate' scope to use.
    """
    log = logging.getLogger(f'{__name__}.CreateUser')

    @method_decorator(protected_resource(scopes=['usercreate']))
    @transaction.atomic()
    def post(self, request) -> HttpResponse:
        cuf = CreateUserForm(request.POST)
        if not cuf.is_valid():
            errors = cuf.errors.as_json()
            self.log.warning('invalid form received: %s', errors)
            if cuf.has_error('email', 'unique'):
                status = 409
            else:
                status = 400
            return HttpResponse(errors, content_type='application/json', status=status)

        self.log.info('Creating user %r on behalf of %s', request.POST['email'], request.user)
        try:
            db_user = UserModel.objects.create_user(
                cuf.cleaned_data['email'],
                cuf.cleaned_data['password'],
                full_name=cuf.cleaned_data['full_name'])
        except IntegrityError as ex:
            # Even though the user didn't exist when we validated the form,
            # it can exist now due to race conditions.
            if 'email' not in str(ex):
                self.log.error('Error creating user %r on behalf of %s: %s',
                               request.POST['email'], request.user, ex)
                errors = {'database': str(ex)}
                status = 500
            else:
                errors = {'email': 'a user with this email address already exists'}
                status = 409
            return JsonResponse(errors, content_type='application/json', status=status)

        LogEntry.objects.log_action(
            user_id=request.user.id,
            content_type_id=ContentType.objects.get_for_model(UserModel).pk,
            object_id=db_user.id,
            object_repr=str(db_user),
            action_flag=ADDITION,
            change_message='Account created via user creation API.')

        return JsonResponse({'user_id': db_user.id}, status=201)


class CheckUserView(AbstractAPIView):
    """API endpoint for checking user account existence.

    Requires an auth token with 'usercreate' scope to use.
    """
    log = logging.getLogger(f'{__name__}.CheckUserView')

    @method_decorator(protected_resource(scopes=['usercreate']))
    def get(self, request, email: str) -> JsonResponse:
        self.log.debug('checking existence of user %r on behalf of %s',
                       email, request.user)
        try:
            UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            found = False
        else:
            found = True
        return JsonResponse({'found': found})
