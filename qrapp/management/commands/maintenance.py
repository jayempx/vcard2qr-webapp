import time
from datetime import datetime, timezone
from django.core.management import call_command
from django.core.management.base import BaseCommand
from qrapp.models import ImportBatch, RateBucket


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--loop", action="store_true")

    def handle(self, *args, **options):
        last_backup = None
        while True:
            now = datetime.now(timezone.utc)
            ImportBatch.objects.filter(expires_at__lte=now).delete()
            RateBucket.objects.filter(expires_at__lte=now).delete()
            call_command("clearsessions")
            if last_backup != now.date():
                call_command("backup_data", prefix="daily")
                last_backup = now.date()
            if not options["loop"]:
                break
            time.sleep(3600)
