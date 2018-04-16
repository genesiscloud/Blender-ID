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


def random_nums():
    """Increasingly larger random number generator."""
    import random

    lower, upper = 1, 5
    while True:
        yield random.randint(lower, upper - 1)
        lower, upper = upper, upper * 3


class CreateUserView(AbstractAPIView):
    """API endpoint for creating users.

    Requires an auth token with 'usercreate' scope to use.
    """

    # Does not require an initial nickname; a unique one is created
    # automatically. This simplifies the API a lot, since a uniqueness
    # constraint violation in the database can be translated directly into a
    # message "this user already exists". If we were to also allow usernames
    # to be chosen here, there is no such mapping any more, and the number of
    # different failure cases increases.

    log = logging.getLogger(f'{__name__}.CreateUser')

    def find_unique_nickname(self, cuf: CreateUserForm) -> str:
        """Return unique nickname based on the user's full name or email."""
        import re

        illegal = re.compile(r'[^\w.+-]')
        strip_email = re.compile('@.*$')

        def acceptable_nickname(name: str) -> bool:
            """Return True iff the nickname is unique."""

            count = UserModel.objects.filter(nickname=name).count()
            return count == 0

        full_name = cuf.cleaned_data['full_name'].replace(' ', '-')
        email = strip_email.sub('', cuf.cleaned_data['email'])
        base = full_name or email
        self.log.debug('Generating unique nickname for base %r', base)

        base = illegal.sub('', base)
        if acceptable_nickname(base):
            return base

        # Try increasingly larger random numbers as a suffix.
        for num in random_nums()[:1000]:
            nickname = f'{base}-{num}'
            if acceptable_nickname(nickname):
                return nickname

        raise ValueError(f'Unable to find unique name for base {base!r} after trying 1000 names')

    @method_decorator(protected_resource(scopes=['usercreate']))
    @transaction.atomic()
    def post(self, request) -> HttpResponse:
        cuf = CreateUserForm(request.POST)
        if not cuf.is_valid():
            errors = cuf.errors.as_json()
            self.log.info('invalid form received: %s', errors)
            if cuf.has_error('email', 'unique'):
                status = 409
            else:
                status = 400
            return HttpResponse(errors, content_type='application/json', status=status)

        self.log.info('Creating user %r on behalf of %s', request.POST['email'], request.user)
        nickname = self.find_unique_nickname(cuf)
        try:
            db_user = UserModel.objects.create_user(
                cuf.cleaned_data['email'],
                cuf.cleaned_data['password'],
                full_name=cuf.cleaned_data['full_name'],
                nickname=nickname,
            )
        except IntegrityError as ex:
            # Even though the user didn't exist when we validated the form,
            # it can exist now due to race conditions.
            if 'nickname' in str(ex):
                self.log.error('Error creating user %r with nickname %r on behalf of %s: %s',
                               request.POST['email'], nickname, request.user, ex)
                errors = {'nickname': 'race condition detected, please try again'}
                status = 400
            elif 'email' not in str(ex):
                self.log.error('Error creating user %r with nickname on behalf of %s: %s',
                               request.POST['email'], nickname, request.user, ex)
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
