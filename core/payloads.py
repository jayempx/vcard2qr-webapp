"""Typed, bounded QR content and interoperable text payloads."""

import hashlib
import math
import re
from datetime import datetime, timezone
from urllib.parse import quote, urlencode, urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ContentError(ValueError):
    def __init__(self, field, message):
        self.field = field
        super().__init__(message)


# Shared by the browser editor, Excel mapping and server validation.
SCHEMA = {
    "vcard": [
        ("first", "First name", "text"),
        ("last", "Last name", "text"),
        ("organization", "Organization", "text"),
        ("title", "Job title", "text"),
        ("email", "Email", "email"),
        ("phone", "Mobile", "tel"),
        ("office", "Office phone", "tel"),
        ("direct", "Direct phone", "tel"),
        ("website", "Website", "url"),
        ("linkedin", "LinkedIn", "url"),
        ("address", "Street address", "text"),
        ("city", "City", "text"),
        ("region", "Region", "text"),
        ("postal", "Postal code", "text"),
        ("country", "Country", "text"),
        ("notes", "Notes", "textarea"),
    ],
    "website": [("url", "Website URL", "url")],
    "text": [("text", "Text", "textarea")],
    "wifi": [
        ("ssid", "Network name (SSID)", "text"),
        ("password", "Password", "password"),
        ("security", "Security", "select"),
        ("hidden", "Hidden network", "checkbox"),
    ],
    "email": [
        ("email", "Recipient", "email"),
        ("subject", "Subject", "text"),
        ("body", "Message", "textarea"),
    ],
    "phone": [("phone", "Phone number", "tel")],
    "sms": [("phone", "Phone number", "tel"), ("message", "Message", "textarea")],
    "location": [("latitude", "Latitude", "number"), ("longitude", "Longitude", "number")],
    "event": [
        ("title", "Event title", "text"),
        ("start", "Start", "datetime-local"),
        ("end", "End", "datetime-local"),
        ("timezone", "Time zone (e.g. Europe/Rome)", "text"),
        ("location", "Location", "text"),
        ("description", "Description", "textarea"),
    ],
    "whatsapp": [("phone", "Phone including country code", "tel"), ("message", "Message", "textarea")],
}
LABELS = dict(
    zip(
        SCHEMA,
        ("vCard", "Website", "Text", "Wi-Fi", "Email", "Phone", "SMS", "Location", "Event", "WhatsApp"),
        strict=True,
    )
)


def checked_url(value, field="url"):
    try:
        parts = urlsplit(value)
        valid = (
            parts.scheme in ("https", "http") and parts.hostname and not parts.username and not parts.password
        )
        _ = parts.port
    except ValueError:
        valid = False
    if not valid or any(c.isspace() or ord(c) < 32 for c in value):
        raise ContentError(field, "Use a complete http:// or https:// address without credentials.")
    return value


def normalize_content(kind, data):
    if kind not in SCHEMA or not isinstance(data, dict):
        raise ContentError("kind", "Choose a supported content type.")
    result = {}
    for key, label, field_type in SCHEMA[kind]:
        raw = data.get(key, False if field_type == "checkbox" else "")
        if field_type == "checkbox":
            if not isinstance(raw, bool):
                raise ContentError(key, "Choose on or off.")
            result[key] = raw
            continue
        if not isinstance(raw, str) or len(raw) > 4000:
            raise ContentError(key, "Use text up to 4,000 characters.")
        value = raw if kind == "wifi" and key in ("ssid", "password") else raw.strip()
        if any(ord(c) < 32 and (field_type != "textarea" or c not in "\r\n\t") for c in value):
            raise ContentError(key, "Remove control characters or line breaks.")
        if value and field_type == "url":
            checked_url(value, key)
        if value and field_type == "email" and not re.fullmatch(r"[^\s@,;:]+@[^\s@,;:]+\.[^\s@,;:]+", value):
            raise ContentError(key, "Enter a valid email address.")
        if value and field_type == "tel" and not re.fullmatch(r"\+?[0-9][0-9 ().#xextEXT-]{1,49}", value):
            raise ContentError(key, "Enter a valid phone number, including country code when needed.")
        result[key] = value
    required = {
        "website": ["url"],
        "text": ["text"],
        "wifi": ["ssid"],
        "email": ["email"],
        "phone": ["phone"],
        "sms": ["phone"],
        "location": ["latitude", "longitude"],
        "event": ["title", "start", "end", "timezone"],
        "whatsapp": ["phone"],
    }.get(kind, [])
    for key in required:
        if not result[key]:
            raise ContentError(key, "This field is required.")
    if kind == "vcard":
        if not any(
            result[k] for k in ("first", "last", "organization", "email", "phone", "office", "direct")
        ):
            raise ContentError("first", "Enter a name, organization, email or phone.")
        custom = data.get("custom", [])
        if not isinstance(custom, list) or len(custom) > 20:
            raise ContentError("custom", "Use at most 20 custom fields.")
        result["custom"] = []
        used = set()
        for item in custom:
            if not isinstance(item, dict) or not all(isinstance(item.get(k), str) for k in ("name", "value")):
                raise ContentError("custom", "Custom fields need a name and value.")
            name, value = item["name"].strip(), item["value"].strip()
            if not name and not value:
                continue
            key = re.sub(r"[ _]+", "-", name.upper()).removeprefix("X-")
            if (
                not re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", key)
                or len(key) > 60
                or key in used
                or not value
                or len(value) > 1000
                or any(ord(c) < 32 and c not in "\n\r\t" for c in value)
            ):
                raise ContentError(
                    "custom", "Use unique alphanumeric names and nonempty values (up to 1,000 characters)."
                )
            used.add(key)
            result["custom"].append({"name": key, "value": value})
    if kind == "wifi":
        result["security"] = result["security"] or "WPA"
        if result["security"] not in ("WPA", "WEP", "nopass"):
            raise ContentError("security", "Choose WPA, WEP or Open.")
        if len(result["ssid"].encode()) > 32:
            raise ContentError("ssid", "SSID must fit in 32 UTF-8 bytes.")
    if kind == "location":
        for key, limit in [("latitude", 90), ("longitude", 180)]:
            try:
                number = float(result[key])
                valid = math.isfinite(number) and abs(number) <= limit
            except ValueError:
                valid = False
            if not valid:
                raise ContentError(key, f"Enter a number between -{limit} and {limit}.")
    if kind == "whatsapp" and not re.fullmatch(
        r"\+?[1-9][0-9]{6,14}", re.sub(r"[ ()-]", "", result["phone"])
    ):
        raise ContentError("phone", "Use an international number with country code, without extensions.")
    if kind == "event":
        start, end = event_times(result)
        if end <= start:
            raise ContentError("end", "End must be after start.")
    return result


def event_times(data):
    try:
        zone = ZoneInfo(data["timezone"])
    except ZoneInfoNotFoundError, ValueError:
        raise ContentError("timezone", "Enter a valid IANA time zone, such as Europe/Rome.") from None
    times = []
    for key in ("start", "end"):
        try:
            naive = datetime.fromisoformat(data[key])
            if naive.tzinfo is not None:
                raise ValueError
            aware = naive.replace(tzinfo=zone)
            if aware.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) != naive:
                raise ValueError
            if aware.utcoffset() != naive.replace(tzinfo=zone, fold=1).utcoffset():
                raise ContentError(
                    key, "This local time is ambiguous at a daylight-saving change; choose another time."
                )
            times.append(aware.astimezone(timezone.utc))
        except (ValueError, TypeError) as exc:
            if isinstance(exc, ContentError):
                raise
            raise ContentError(key, "Enter a valid, unambiguous local date and time.") from None
    return times


def escaped(text):
    return (
        text.replace("\\", "\\\\")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


def lines_payload(lines):
    folded = []
    for line in lines:
        chunk = ""
        for char in line:
            if len((chunk + char).encode()) > 75:
                folded.append(chunk)
                chunk = " "
            chunk += char
        folded.append(chunk)
    return "\r\n".join(folded) + "\r\n"


def build_payload(kind, data):
    d = normalize_content(kind, data)
    if kind == "website":
        return d["url"]
    if kind == "text":
        return d["text"]
    if kind == "vcard":
        name = " ".join(filter(None, (d["first"], d["last"]))) or next(
            d[k] for k in ("organization", "email", "phone", "office", "direct") if d[k]
        )
        lines = [
            "BEGIN:VCARD",
            "VERSION:3.0",
            f"N:{escaped(d['last'])};{escaped(d['first'])};;;",
            f"FN:{escaped(name)}",
        ]
        props = {
            "organization": "ORG",
            "title": "TITLE",
            "email": "EMAIL;TYPE=INTERNET",
            "phone": "TEL;TYPE=CELL",
            "office": "TEL;TYPE=WORK",
            "direct": "TEL;TYPE=WORK,VOICE",
            "website": "URL",
            "linkedin": "URL",
            "notes": "NOTE",
        }
        lines.extend(f"{prop}:{escaped(d[k])}" for k, prop in props.items() if d[k])
        address = [d[k] for k in ("address", "city", "region", "postal", "country")]
        if any(address):
            lines.append("ADR;TYPE=WORK:;;" + ";".join(escaped(v) for v in address))
        lines.extend(f"X-{v['name']}:{escaped(v['value'])}" for v in d["custom"])
        return lines_payload([*lines, "END:VCARD"])
    if kind == "wifi":

        def wifi(value):
            return re.sub(r"([\\;,:\"])", r"\\\1", value)

        return f"WIFI:T:{d['security']};S:{wifi(d['ssid'])};P:{wifi(d['password'])};H:{str(d['hidden']).lower()};;"
    phone = quote(d.get("phone", ""), safe="+")
    if kind == "phone":
        return "tel:" + phone
    if kind == "sms":
        return "sms:" + phone + "?" + urlencode({"body": d["message"]}, quote_via=quote)
    if kind == "email":
        return (
            "mailto:"
            + quote(d["email"], safe="@")
            + "?"
            + urlencode({"subject": d["subject"], "body": d["body"]}, quote_via=quote)
        )
    if kind == "whatsapp":
        return (
            "https://wa.me/"
            + re.sub(r"\D", "", d["phone"])
            + "?"
            + urlencode({"text": d["message"]}, quote_via=quote)
        )
    if kind == "location":
        return f"geo:{d['latitude']},{d['longitude']}"
    start, end = event_times(d)
    uid = hashlib.sha256(repr(sorted(d.items())).encode()).hexdigest()[:32]
    return lines_payload(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//QR Studio//EN",
            "BEGIN:VEVENT",
            f"UID:{uid}@qr.invalid",
            "DTSTAMP:" + start.strftime("%Y%m%dT%H%M%SZ"),
            "DTSTART:" + start.strftime("%Y%m%dT%H%M%SZ"),
            "DTEND:" + end.strftime("%Y%m%dT%H%M%SZ"),
            "SUMMARY:" + escaped(d["title"]),
            "LOCATION:" + escaped(d["location"]),
            "DESCRIPTION:" + escaped(d["description"]),
            "END:VEVENT",
            "END:VCALENDAR",
        ]
    )
