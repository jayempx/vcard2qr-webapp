"""Back up an existing database, migrate, then start the non-root server."""

import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import django

django.setup()
from django.db import connection
from django.core.management import call_command

if "qrapp_qrrecord" in connection.introspection.table_names():
    call_command("backup_data", prefix="predeploy")
call_command("migrate", interactive=False, verbosity=0)
os.execvp(
    "gunicorn",
    [
        "gunicorn",
        "config.wsgi:application",
        "--bind",
        "0.0.0.0:8000",
        "--workers",
        "2",
        "--threads",
        "4",
        "--timeout",
        "120",
        "--error-logfile",
        "-",
    ],
)
