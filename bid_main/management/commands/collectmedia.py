from pathlib import Path
import shutil

from django.conf import settings
from django.core.management import CommandError, BaseCommand
from django.apps.registry import apps


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--noinput',
                            action='store_false', dest='interactive', default=True,
                            help="Do NOT prompt the user for input of any kind."),

    def handle(self, *args, **options):
        app_fixtures = [Path(config.path) / 'fixtures'
                        for config in apps.get_app_configs()]
        app_fixtures += [Path(path) for path in settings.FIXTURE_DIRS]

        if options['interactive']:
            confirm = input("This will overwrite existing files. Proceed? ")
            if not confirm.lower().startswith('y'):
                raise CommandError("Media syncing aborted")

        media_root = Path(settings.MEDIA_ROOT)
        for fixtures_root in app_fixtures:
            if options['verbosity'] > 1:
                self.stdout.write(f'App {fixtures_root}')

            fixture_media = fixtures_root / 'media'
            if not fixture_media.exists():
                # No media files exist, so no need to inspect the fixture itself.
                if options['verbosity'] > 2:
                    self.stdout.write(f'   - no fixtures/media dir')
                continue

            for file_path in fixture_media.rglob('*'):
                if file_path.is_dir():
                    continue

                rel_to_fixture = file_path.relative_to(fixture_media)
                final_dest = media_root / rel_to_fixture
                final_dest.parent.mkdir(parents=True, exist_ok=True)

                shutil.copy(file_path, final_dest)

                if options['verbosity'] > 0:
                    relpath = file_path.absolute().relative_to(settings.BASE_DIR)
                    reldest = final_dest.absolute().relative_to(settings.BASE_DIR)
                    self.stdout.write(self.style.SUCCESS(f'{relpath} → {reldest}'))
