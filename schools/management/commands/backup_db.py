from django.core.management.base import BaseCommand
from django.conf import settings
from datetime import datetime
import shutil
import os


class Command(BaseCommand):
    help = 'Backup the SQLite database'

    def handle(self, *args, **options):
        db_path = settings.DATABASES['default']['NAME']
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')

        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'db_backup_{timestamp}.sqlite3'
        backup_path = os.path.join(backup_dir, backup_filename)

        shutil.copy2(db_path, backup_path)
        self.stdout.write(self.style.SUCCESS(f'Database backed up to {backup_path}'))
