import logging
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from bid_api import models

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Flushes the webhook queue'

    def add_arguments(self, parser):
        parser.add_argument('--flush', '-f',
                            action='store_true',
                            default=False,
                            help='Really perform the flush; without this only the '
                                 'size of the queue is shown.')
        parser.add_argument('--monitor', '-m',
                            action='store_true',
                            default=False,
                            help='Continually monitors the webhook queues.')

    def handle(self, *args, **options):
        do_flush = options['flush']
        verbose = options['verbosity'] > 0

        levels = {
            0: logging.ERROR,
            1: logging.WARNING,
            2: logging.INFO,
            3: logging.DEBUG,
        }
        level = levels.get(options['verbosity'], logging.DEBUG)
        logging.getLogger('bid_api').setLevel(level)
        logging.disable(level - 1)
        if options['monitor']:
            return self.monitor()

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

    def monitor(self):
        """Keeps monitoring the queues."""

        try:
            while True:
                self._monitor_iteration()
                time.sleep(1)
        except KeyboardInterrupt:
            log.info('shutting down webhook queue monitor')

    def _monitor_iteration(self):
        """Single iteration of queue monitor."""

        # Investigate the hook status every time, since they can have been
        # enabled/disabled since our last iteration.
        hooks = models.Webhook.objects.filter(enabled=True)
        if not hooks:
            log.debug('no enabled hooks')
            return

        # Skip hooks that don't have to be flushed.
        flush_info = []
        for hook in hooks:
            ft = hook.flush_time()
            if ft is None:  # Means that there is nothing queued.
                continue
            flush_info.append((ft, hook))
        if not flush_info:
            log.debug('nothing to flush')
            return

        flush_time, flush_hook = min(flush_info)
        secs_in_future = (flush_time - timezone.now()).total_seconds()
        if secs_in_future > 1:
            log.debug('soonest to flush is %s, but is %d seconds in future; waiting',
                      flush_hook, secs_in_future)
            return
        flush_hook.flush()
