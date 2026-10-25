from django.db import transaction
from django.db.models import F
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_safe

from core.payloads import LABELS, SCHEMA, build_payload
from .models import QRRecord


@require_safe
def destination(request, id, download=None):
    with transaction.atomic():
        row = QRRecord.objects.select_for_update().filter(pk=id, active=True).first()
        if row is None:
            return render(request, "qrapp/unavailable.html", status=404)
        if download:
            expected = "vcard" if download == "contact.vcf" else "event"
            if row.kind != expected:
                return render(request, "qrapp/unavailable.html", status=404)
            response = HttpResponse(
                build_payload(row.kind, row.data),
                content_type="text/vcard; charset=utf-8"
                if expected == "vcard"
                else "text/calendar; charset=utf-8",
            )
            response["Content-Disposition"] = f'attachment; filename="{download}"'
            return response
        if request.method == "GET":
            QRRecord.objects.filter(pk=id).update(
                total_opens=F("total_opens") + 1, last_opened_at=timezone.now()
            )
        if row.kind == "website":
            return HttpResponseRedirect(row.data["url"])
    fields = [(label, row.data.get(key)) for key, label, _ in SCHEMA[row.kind] if row.data.get(key)]
    fields.extend((item["name"], item["value"]) for item in row.data.get("custom", []))
    action = None
    action_label = None
    if row.kind in ("phone", "sms", "email", "location", "whatsapp"):
        action = build_payload(row.kind, row.data)
        action_label = {
            "phone": "Call",
            "sms": "Send message",
            "email": "Write email",
            "location": "Open map",
            "whatsapp": "Open WhatsApp",
        }[row.kind]
    title = (
        " ".join(filter(None, [row.data.get("first"), row.data.get("last")]))
        or row.data.get("organization")
        or LABELS[row.kind]
    )
    return render(
        request,
        "qrapp/destination.html",
        {"row": row, "fields": fields, "title": title, "action": action, "action_label": action_label},
    )
