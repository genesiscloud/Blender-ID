"""
Badger service functionality.
"""

import logging

from django.db import transaction, IntegrityError
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.contrib.admin.models import LogEntry, ADDITION, DELETION
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils.decorators import method_decorator
from oauth2_provider.decorators import protected_resource

from bid_main import models as bid_main_models
from ..http_responses import HttpResponseUnprocessableEntity
from .abstract import AbstractAPIView

log = logging.getLogger(__name__)
UserModel = get_user_model()


class BadgerView(AbstractAPIView):
    action = 'grant'

    @method_decorator(protected_resource(scopes=['badger']))
    def post(self, request, badge: str, email_or_uid: str) -> HttpResponse:
        return self.do_badger(request, badge, email_or_uid)

    @transaction.atomic()
    def do_badger(self, request, badge: str, email_or_uid: str) -> HttpResponse:
        """Performs the actual badger service, can be called without OAuth token

        This makes it possible for management commands to use this functionality.
        """
        user = request.user
        action = self.action

        # See which roles this user can manage.
        may_manage = {}
        for role in user.roles.all():
            for manage_role in role.may_manage_roles.all():
                may_manage[manage_role.name] = manage_role

        if badge not in may_manage:
            log.warning(
                'User %s tried to %s role %r to user %s, is not allowed to grant that role',
                user, action, badge, email_or_uid)
            return HttpResponseForbidden()

        # Check the role for being an active badge.
        role = may_manage[badge]
        if not role.is_active:
            log.warning('User %s tried to %s non-active role %r to user %s',
                        user, action, badge, email_or_uid)
            return HttpResponseForbidden()

        # Try to find the target user.
        try:
            user_id = int(email_or_uid, 10)
        except ValueError:
            match_user = {'email': email_or_uid}
        else:
            match_user = {'id': user_id}

        try:
            target_user: bid_main_models.User = UserModel.objects.get(**match_user)
        except UserModel.DoesNotExist:
            log.warning('User %s tried to %s role %r to nonexistent user %s',
                        user, action, badge, email_or_uid)
            return HttpResponseUnprocessableEntity()
        email = target_user.email

        # Grant/revoke the role to/from the target user.
        if action == 'grant':
            log.info('User %s grants role %r to user %s', user, badge, email)
            action_flag = ADDITION
            if role in target_user.roles.all():
                log.debug('User %s already has role %r', email, badge)
                return JsonResponse({'result': 'no-op'})
            try:
                target_user.roles.add(role)
            except IntegrityError:
                # This generally means that the uniqueness constraint was
                # invalidated, which means that the role was already granted.
                log.exception('Integrity error granting role %r to user %s, skipping this role',
                              role, target_user)
                return JsonResponse({'result': 'no-op'})
            change_message = f'Granted role {badge}.'
        elif action == 'revoke':
            log.info('User %s revokes role %r from user %s', user, badge, email)
            action_flag = DELETION
            if role not in target_user.roles.all():
                log.debug('User %s already does not have role %r', email, badge)
                return JsonResponse({'result': 'no-op'})
            target_user.roles.remove(role)
            change_message = f'Revoked role {badge}.'
        else:
            log.warning('unknown action %r', action)
            return HttpResponseUnprocessableEntity('unknown action')
        target_user.save()

        LogEntry.objects.log_action(
            user_id=user.id,
            content_type_id=ContentType.objects.get_for_model(UserModel).pk,
            object_id=target_user.id,
            object_repr=str(target_user),
            action_flag=action_flag,
            change_message=change_message)

        return JsonResponse({'result': 'ok'})
