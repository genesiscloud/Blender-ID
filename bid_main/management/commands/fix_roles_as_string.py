"""Updates users' public_roles_as_string property based on their roles."""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from bid_main import models


class Command(BaseCommand):
    help = "Updates users' public_roles_as_string property based on their roles"

    def handle(self, *args, **options):
        from bid_api import signals
        from django.db.models.signals import post_save

        post_save.disconnect(signals.modified_user_to_webhooks)

        self.stdout.write('Updating all users.')

        model: models.User = get_user_model()
        all_users = model.objects.all()
        user_count = len(all_users)
        for idx, user in enumerate(all_users):
            do_print = (
                (user_count > 250 and idx % 250 == 0) or
                (user_count > 100 and idx % 10 == 0) or
                (user_count <= 100)
            )
            if do_print:
                self.stdout.write(f'   - {idx+1}/{user_count}')

            roles = user.public_roles()
            user.public_roles_as_string = ' '.join(sorted(roles))
            user.save(update_fields={'public_roles_as_string'})

        self.stdout.write(self.style.SUCCESS(f'Done, updated {user_count} users.'))
