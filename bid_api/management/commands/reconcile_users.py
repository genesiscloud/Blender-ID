#!/usr/bin/env python3

"""Simple command for one-time use after making Blender ID owner of subscription status."""

import json
import logging

from django.db.transaction import atomic
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.core.management.base import BaseCommand

from bid_api.views.badger import BadgerView

log = logging.getLogger(__name__)
UserModel = get_user_model()
API_USER = 'sybren@stuvel.eu'


class Command(BaseCommand):
    managed_roles = {'cloud_subscriber', 'cloud_has_subscription'}
    help = 'Reconciles subscription status based on info in reconcile_subscribers.json'

    @atomic()
    def handle(self, *args, **options):
        self.stdout.write('Going.')
        self.api_user = UserModel.objects.get(email=API_USER)

        with open('reconcile_subscribers.json') as infile:
            email_to_roles = json.load(infile)

        with open('reconcile_subscribers_errors.txt', 'w') as errfile:
            for email, roles in email_to_roles.items():
                try:
                    self.do_user(email, roles)
                except KeyboardInterrupt:
                    raise SystemExit('Stopping')
                except Exception as ex:
                    log.exception('Error updating user %s', email)
                    print(email, file=errfile)

    def do_user(self, email, roles):
        to_grant = set(roles)
        to_revoke = self.managed_roles - to_grant

        request = HttpRequest()
        request.user = self.api_user

        view = BadgerView()

        for role in to_grant:
            resp = view.do_badger(request, role, email)
            if resp.status_code == 422:
                return
            if resp.status_code != 200:
                raise ValueError('Error %s for email %s' % (resp.status_code, email))

        for role in to_revoke:
            resp = view.do_badger(request, role, email)
            if resp.status_code == 422:
                return
            if resp.status_code != 200:
                raise ValueError('Error %s for email %s' % (resp.status_code, email))
