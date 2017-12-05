import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from bid_api import models

log = logging.getLogger(__name__)
UserModel = get_user_model()
API_USER = 'sybren@stuvel.eu'


class Command(BaseCommand):
    help = 'Flushes the webhook queue'

    def add_arguments(self, parser):
        parser.add_argument('--flush', '-f',
                            action='store_true',
                            default=False,
                            help='Really perform the flush; without this only the '
                                 'size of the queue is shown.')

    def handle(self, *args, **options):
        do_flush = options['flush']
        verbose = options['verbosity'] > 0

        levels = {
            0: logging.WARNING,
            1: logging.INFO,
        }
        level = levels.get(options['verbosity'], logging.DEBUG)
        logging.getLogger('bid_api').setLevel(level)

        queue = models.WebhookQueuedCall.objects

        count = queue.count()
        if verbose:
            if count == 0:
                self.stdout.write(self.style.SUCCESS(f'The queue is empty'))
            elif count == 1:
                self.stdout.write(self.style.WARNING(f'There is 1 queued item'))
            else:
                self.stdout.write(self.style.WARNING(f'There are {count} queued items'))

        if not do_flush:
            if count > 0:
                self.stdout.write('Use the --flush CLI option to perform flush.')
            return

        if verbose:
            self.stdout.write('Flushing...')
        models.WebhookQueuedCall.flush_all()
        if verbose:
            self.stdout.write('Flush performed...')

            new_count = queue.count()
            if new_count == 0:
                self.stdout.write(self.style.SUCCESS('The queue is now empty'))
            elif new_count == 1:
                self.stdout.write(self.style.WARNING(f'There is still 1 item queued.'))
            else:
                self.stdout.write(self.style.WARNING(f'There are still {new_count} items queued.'))
