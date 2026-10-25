import json
import time
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from qrapp.models import QRRecord


@override_settings(ACCESS_CODE="012345", PUBLIC_BASE_URL="https://qr.example.com")
class WebTests(TestCase):
    def test_lock_revokes_copied_session_cookie(self):
        self.unlock()
        from django.conf import settings

        replay = Client()
        replay.cookies[settings.SESSION_COOKIE_NAME] = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        self.post("/api/lock/", {})
        self.assertEqual(replay.get("/api/records/").status_code, 401)

    def post(self, url, data, client=None):
        return (client or self.client).post(url, data=json.dumps(data), content_type="application/json")

    def unlock(self):
        self.assertEqual(self.post("/api/unlock/", {"code": "012345"}).status_code, 200)

    def create(self, kind="vcard", data=None):
        response = self.post(
            "/api/records/",
            {"name": "Sample", "kind": kind, "data": data or {"first": "Alex"}, "appearance": {}},
        )
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def test_gate_expiry_rotation_and_lock(self):
        self.assertEqual(self.client.get("/api/records/").status_code, 401)
        self.assertEqual(self.post("/api/unlock/", {"code": "999999"}).status_code, 403)
        self.unlock()
        self.assertEqual(self.client.get("/api/records/").status_code, 200)
        with override_settings(ACCESS_CODE="654321"):
            self.assertEqual(self.client.get("/api/records/").status_code, 401)
        with patch("qrapp.access.time.time", return_value=time.time() + 90000):
            self.assertEqual(self.client.get("/api/records/").status_code, 401)
        self.post("/api/lock/", {})
        self.assertEqual(self.client.get("/api/records/").status_code, 401)

    def test_brute_force_and_csrf(self):
        for _ in range(5):
            self.post("/api/unlock/", {"code": "000000"})
        self.assertEqual(self.post("/api/unlock/", {"code": "012345"}).status_code, 429)
        strict = Client(enforce_csrf_checks=True)
        self.assertEqual(self.post("/api/unlock/", {"code": "012345"}, strict).status_code, 403)

    def test_static_is_not_persisted_and_export_is_decodable(self):
        response = self.post(
            "/api/export/", {"kind": "text", "data": {"text": "Hello"}, "appearance": {}, "format": "png"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"\x89PNG"))
        self.assertEqual(QRRecord.objects.count(), 0)
        self.assertEqual(self.post("/api/records/", {}).status_code, 401)

    def test_record_lifecycle_and_counts(self):
        self.unlock()
        record = self.create()
        url = record["url"]
        path = "/q/" + record["id"] + "/"
        public = Client()
        self.assertContains(public.get(path), "Save contact")
        public.head(path)
        self.assertIn(b"BEGIN:VCARD", public.get(path + "contact.vcf").content)
        row = QRRecord.objects.get(pk=record["id"])
        self.assertEqual(row.total_opens, 1)
        endpoint = "/api/records/" + record["id"] + "/"
        changed = self.client.patch(
            endpoint,
            data=json.dumps(
                {
                    "name": "Website",
                    "kind": "website",
                    "data": {"url": "https://example.com"},
                    "appearance": {},
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(changed.json()["url"], url)
        response = public.get(path)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://example.com")
        self.assertIn("no-store", response["Cache-Control"])
        self.client.patch(endpoint, data='{"active":false}', content_type="application/json")
        self.assertEqual(public.get(path).status_code, 404)
        row.refresh_from_db()
        self.assertEqual(row.total_opens, 2)
        self.assertEqual(public.get(endpoint).status_code, 401)
        self.assertEqual(self.client.delete(endpoint).status_code, 204)
        self.assertEqual(public.get(path).status_code, 404)

    def test_errors_and_no_script_injection(self):
        self.unlock()
        bad = self.post(
            "/api/records/",
            {"name": "Unsafe", "kind": "website", "data": {"url": "javascript:alert(1)"}, "appearance": {}},
        )
        self.assertEqual(bad.status_code, 400)
        record = self.create("text", {"text": "<script>alert(1)</script>"})
        self.assertContains(self.client.get("/q/" + record["id"] + "/"), "&lt;script&gt;")
        self.assertEqual(
            self.post(
                "/api/export/", {"kind": "text", "data": {"text": "x"}, "appearance": {"size": 999999}}
            ).status_code,
            400,
        )
