import io
import json
import zipfile
from datetime import timedelta

from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from openpyxl import Workbook

from qrapp.models import QRRecord


@override_settings(ACCESS_CODE="012345")
class ImportTests(TestCase):
    def test_render_only_during_cancellable_steps(self):
        from unittest.mock import patch
        from core.qr import render_export

        self.post("/api/unlock/", {"code": "012345"})
        id = self.upload([["url"], ["https://example.com"]]).json()["id"]
        with patch("qrapp.batch_views.render_export", wraps=render_export) as renderer:
            self.post(
                "/api/imports/validate/",
                {
                    "id": id,
                    "sheet": "Sheet",
                    "kind": "website",
                    "mode": "static",
                    "mapping": ["url"],
                    "appearance": {},
                },
            )
            self.assertEqual(renderer.call_count, 0)
            self.post("/api/imports/" + id + "/step/", {"cursor": 0})
            self.assertEqual(renderer.call_count, 2)
            renderer.reset_mock()
            self.client.get("/api/imports/" + id + "/download/")
            self.assertEqual(renderer.call_count, 0)

    def test_downloadable_templates_are_protected_and_importable(self):
        self.assertEqual(self.client.get("/api/imports/template/?kind=vcard").status_code, 401)
        self.post("/api/unlock/", {"code": "012345"})
        for kind in ("vcard", "website"):
            response = self.client.get("/api/imports/template/?kind=" + kind)
            self.assertEqual(response.status_code, 200)
            upload = self.client.post(
                "/api/imports/inspect/", {"file": SimpleUploadedFile("template.xlsx", response.content)}
            )
            self.assertEqual(upload.status_code, 200)
            self.assertIn("Data", upload.json()["sheets"])

    def post(self, url, data):
        return self.client.post(url, json.dumps(data), content_type="application/json")

    def upload(self, rows):
        wb = Workbook()
        for row in rows:
            wb.active.append(row)
        stream = io.BytesIO()
        wb.save(stream)
        return self.client.post(
            "/api/imports/inspect/", {"file": SimpleUploadedFile("contacts.xlsx", stream.getvalue())}
        )

    def test_protected_and_malformed(self):
        self.assertEqual(self.upload([["Name"], ["A"]]).status_code, 401)
        self.post("/api/unlock/", {"code": "012345"})
        self.assertEqual(
            self.client.post(
                "/api/imports/inspect/", {"file": SimpleUploadedFile("bad.xlsx", b"not zip")}
            ).status_code,
            400,
        )

    def test_mixed_rows_retry_cancel_and_zip(self):
        self.post("/api/unlock/", {"code": "012345"})
        uploaded = self.upload(
            [
                ["Name", "Email", "Phone"],
                ["Alex", "a@example.com", "0012345"],
                ["Bad", "invalid", "1234"],
                ["Formula", "=1+1", "12345"],
                ["Numeric", "n@example.com", 12345],
            ]
        )
        self.assertEqual(uploaded.status_code, 200, uploaded.content)
        id = uploaded.json()["id"]
        validated = self.post(
            "/api/imports/validate/",
            {
                "id": id,
                "sheet": "Sheet",
                "kind": "vcard",
                "mode": "persistent",
                "mapping": ["first", "email", "phone"],
                "appearance": {},
            },
        )
        self.assertEqual(validated.status_code, 200, validated.content)
        self.assertEqual(validated.json()["valid"], 2)
        self.assertEqual(validated.json()["invalid"], 2)
        path = "/api/imports/" + id + "/"
        step = self.post(path + "step/", {"cursor": 0})
        self.assertEqual(step.status_code, 200, step.content)
        self.assertEqual(QRRecord.objects.count(), 2)
        self.post(path + "step/", {"cursor": 0})
        self.assertEqual(QRRecord.objects.count(), 2)
        content = self.client.get(path + "download/?format=svg")
        self.assertEqual(content.status_code, 200, content.content[:200])
        archive = zipfile.ZipFile(io.BytesIO(content.content))
        self.assertEqual(len([n for n in archive.namelist() if n.endswith(".svg")]), 2)
        self.assertIn("report.json", archive.namelist())

    def test_website_static_does_not_create_records_and_expiry(self):
        self.post("/api/unlock/", {"code": "012345"})
        uploaded = self.upload([["URL"], ["https://example.com"], ["javascript:bad"]])
        id = uploaded.json()["id"]
        self.post(
            "/api/imports/validate/",
            {
                "id": id,
                "sheet": "Sheet",
                "kind": "website",
                "mode": "static",
                "mapping": ["url"],
                "appearance": {},
            },
        )
        self.post("/api/imports/" + id + "/step/", {"cursor": 0})
        self.assertEqual(QRRecord.objects.count(), 0)
        from qrapp.models import ImportBatch

        ImportBatch.objects.filter(pk=id).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.client.get("/api/imports/" + id + "/download/").status_code, 404)

    def test_mapping_collision_and_cancellation(self):
        self.post("/api/unlock/", {"code": "012345"})
        uploaded = self.upload([["First", "Last"], ["A", "B"]])
        id = uploaded.json()["id"]
        config = {
            "id": id,
            "sheet": "Sheet",
            "kind": "vcard",
            "mode": "persistent",
            "mapping": ["first", "first"],
            "appearance": {},
        }
        self.assertEqual(self.post("/api/imports/validate/", config).status_code, 400)
        config["mapping"] = ["first", "last"]
        self.assertEqual(self.post("/api/imports/validate/", config).status_code, 200)
        self.post("/api/imports/" + id + "/cancel/", {})
        self.post("/api/imports/" + id + "/step/", {"cursor": 0})
        self.assertEqual(QRRecord.objects.count(), 0)
