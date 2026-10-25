from concurrent.futures import ThreadPoolExecutor
from unittest import skipUnless

from django.db import connection, connections
from django.test import Client, TransactionTestCase
from qrapp.models import QRRecord


@skipUnless(connection.vendor == "postgresql", "PostgreSQL integration test")
class ConcurrentOpenTests(TransactionTestCase):
    def test_no_lost_opens(self):
        row = QRRecord.objects.create(name="Concurrency", kind="website", data={"url": "https://example.com"})

        def visit(_):
            try:
                return Client().get("/q/" + row.id + "/").status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=8) as workers:
            self.assertEqual(list(workers.map(visit, range(40))), [302] * 40)
        row.refresh_from_db()
        self.assertEqual(row.total_opens, 40)
