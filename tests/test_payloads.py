import io
import unittest

from PIL import Image
import zxingcpp

from core.payloads import build_payload, normalize_content
from core.qr import render_export


class PayloadTests(unittest.TestCase):
    def test_vcard_unicode_delimiters_and_folding(self):
        value = build_payload(
            "vcard",
            {
                "first": "Zoë",
                "last": "Example",
                "notes": "Hello;\nORG:injected",
                "custom": [{"name": "Department", "value": "é" * 90}],
            },
        )
        self.assertIn("FN:Zoë Example\r\n", value)
        self.assertIn("NOTE:Hello\\;\\nORG:injected", value)
        self.assertNotIn("\r\nORG:injected", value)
        self.assertTrue(all(len(line.encode()) <= 75 for line in value.split("\r\n")))

    def test_typed_payloads(self):
        examples = {
            "website": ({"url": "https://example.com/a"}, "https://"),
            "text": ({"text": "Hello 🌍"}, "Hello"),
            "wifi": (
                {"ssid": "Guest;net", "password": "abc:123", "security": "WPA"},
                "WIFI:T:WPA;S:Guest\\;net;",
            ),
            "email": ({"email": "hello@example.com", "subject": "A & B"}, "mailto:"),
            "phone": ({"phone": "+1 202 555 0100"}, "tel:"),
            "sms": ({"phone": "+12025550100", "message": "Hello & hi"}, "sms:"),
            "location": ({"latitude": "12.5", "longitude": "-45"}, "geo:"),
            "event": (
                {"title": "Demo", "start": "2027-01-01T09:00", "end": "2027-01-01T10:00", "timezone": "UTC"},
                "BEGIN:VCALENDAR",
            ),
            "whatsapp": ({"phone": "+12025550100", "message": "Hi"}, "https://wa.me/"),
        }
        for kind, (data, prefix) in examples.items():
            with self.subTest(kind=kind):
                self.assertTrue(build_payload(kind, data).startswith(prefix))

    def test_invalid_data(self):
        cases = [
            ("website", {"url": "javascript:alert(1)"}),
            ("website", {"url": "https://user:pass@example.com"}),
            ("location", {"latitude": "NaN", "longitude": "0"}),
            ("location", {"latitude": "91", "longitude": "0"}),
            ("email", {"email": "x@example.com\r\nBcc:x@example.com"}),
            (
                "event",
                {"title": "x", "start": "2027-01-01T10:00", "end": "2027-01-01T09:00", "timezone": "UTC"},
            ),
            ("vcard", {"custom": [{"name": "X\nORG", "value": "bad"}]}),
            ("text", {"text": ""}),
        ]
        for kind, data in cases:
            with self.subTest(kind=kind, data=data):
                with self.assertRaises(ValueError):
                    normalize_content(kind, data)

    def test_png_and_svg_decode(self):
        import resvg_py

        payload = build_payload("vcard", {"first": "Zoë", "email": "demo@example.com"})
        for fmt in ("png", "svg"):
            for rounded in (False, True):
                with self.subTest(fmt=fmt, rounded=rounded):
                    data = render_export(payload, {"size": 768, "rounded": rounded, "transparent": True}, fmt)
                    if fmt == "svg":
                        data = resvg_py.svg_to_bytes(svg_string=data.decode())
                    image = Image.open(io.BytesIO(data)).convert("RGBA")
                    white = Image.new("RGBA", image.size, "white")
                    white.alpha_composite(image)
                    decoded = zxingcpp.read_barcode(white.convert("RGB"))
                    self.assertIsNotNone(decoded)
                    self.assertEqual(decoded.text, payload)

    def test_bad_contrast_size_capacity(self):
        for payload, opts in [("ok", {"foreground": "#ffffff"}), ("ok", {"size": 20}), ("x" * 10000, {})]:
            with self.assertRaises(ValueError):
                render_export(payload, opts, "png")
