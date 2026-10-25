import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from secrets import token_hex

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a PostgreSQL custom-format backup; keep at most 14 per prefix."

    def add_arguments(self, parser):
        parser.add_argument("--prefix", choices=["daily", "predeploy"], default="daily")

    def handle(self, *args, **options):
        db = settings.DATABASES["default"]
        if db["ENGINE"] != "django.db.backends.postgresql":
            raise CommandError("Backups require PostgreSQL.")
        directory = Path(os.environ.get("BACKUP_DIR", "/backups"))
        directory.mkdir(parents=True, exist_ok=True)
        prefix = options["prefix"]
        # Bound restart-loop accumulation before writing another snapshot.
        backups = sorted(directory.glob(prefix + "-*.dump"))
        for old in backups[:-13]:
            old.unlink()
        name = prefix + "-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + token_hex(4)
        temp = directory / (name + ".partial")
        env = dict(
            os.environ,
            PGPASSWORD=db["PASSWORD"],
            PGHOST=db["HOST"],
            PGPORT=str(db["PORT"]),
            PGUSER=db["USER"],
        )
        try:
            subprocess.run(
                ["pg_dump", "--format=custom", "--no-owner", "--file", str(temp), db["NAME"]],
                env=env,
                check=True,
                capture_output=True,
            )
            subprocess.run(["pg_restore", "--list", str(temp)], env=env, check=True, capture_output=True)
            temp.replace(directory / (name + ".dump"))
        except subprocess.CalledProcessError:
            raise CommandError("Database backup failed; deployment stopped.") from None
        finally:
            temp.unlink(missing_ok=True)
        self.stdout.write("Verified backup written.")
