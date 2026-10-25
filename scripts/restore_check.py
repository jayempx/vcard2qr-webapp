"""Explicitly enabled isolated restore drill; never targets the live database."""

import os
import subprocess
import sys
from pathlib import Path
from secrets import token_hex
from datetime import datetime, timezone, timedelta

if os.environ.get("ALLOW_RESTORE_TEST") != "1":
    raise SystemExit("Restore test must be explicitly enabled on an isolated test deployment.")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
from django.conf import settings
from django.core.management import call_command
from qrapp.models import QRRecord, ImportBatch
import psycopg
from psycopg import sql

db = settings.DATABASES["default"]
params = dict(host=db["HOST"], port=db["PORT"], user=db["USER"], password=db["PASSWORD"])
name = "restore_check_" + token_hex(8)
row = QRRecord.objects.create(
    name="Restore test", kind="text", data={"text": "Synthetic restore fixture"}, total_opens=7
)
created = False
temporary = ImportBatch.objects.create(
    rows=[{"data": {"text": "Temporary static content"}}],
    expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
)
try:
    call_command("backup_data")
    dump = sorted(Path("/backups").glob("daily-*.dump"))[-1]
    with psycopg.connect(dbname="postgres", autocommit=True, **params) as control:
        control.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        created = True
    env = dict(
        os.environ, PGPASSWORD=db["PASSWORD"], PGHOST=db["HOST"], PGUSER=db["USER"], PGPORT=str(db["PORT"])
    )
    subprocess.run(
        ["pg_restore", "--exit-on-error", "--no-owner", "--dbname", name, str(dump)],
        env=env,
        check=True,
        capture_output=True,
    )
    with psycopg.connect(dbname=name, **params) as restored:
        actual = restored.execute(
            "SELECT id, total_opens FROM qrapp_qrrecord WHERE id = %s", [row.id]
        ).fetchone()
        assert actual == (row.id, 7), "Restored record identity/count mismatch"
        assert restored.execute("SELECT count(*) FROM qrapp_importbatch").fetchone()[0] == 0, (
            "Temporary import data must not be retained in backups"
        )
    print("Isolated PostgreSQL restore: stable record ID and counter verified.")
finally:
    if created:
        with psycopg.connect(dbname="postgres", autocommit=True, **params) as control:
            control.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))
    row.delete()
    temporary.delete()
