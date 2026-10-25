import hmac
import json
import time
from functools import wraps

from django.conf import settings
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST

from core.payloads import ContentError, LABELS, SCHEMA, build_payload, normalize_content
from core.qr import appearance_settings, render_export
from .access import consume, digest, private, unlocked
from .models import QRRecord


def api(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except (ValueError, TypeError) as exc:
            return JsonResponse(
                {
                    "error": str(exc) if isinstance(exc, ValueError) else "Invalid input type.",
                    "field": getattr(exc, "field", ""),
                },
                status=400,
            )

    return wrapped


def body(request):
    if len(request.body) > 32000:
        raise ValueError("Request is too large.")
    try:
        data = json.loads(request.body)
    except UnicodeDecodeError, json.JSONDecodeError:
        raise ValueError("Send a valid JSON object.") from None
    if not isinstance(data, dict):
        raise ValueError("Send a JSON object.")
    return data


def serialized(row):
    return {
        "id": row.id,
        "name": row.name,
        "kind": row.kind,
        "data": row.data,
        "appearance": row.appearance,
        "active": row.active,
        "opens": row.total_opens,
        "last_opened": row.last_opened_at.isoformat() if row.last_opened_at else None,
        "url": settings.PUBLIC_BASE_URL + "/q/" + row.id + "/",
        "updated_at": row.updated_at.isoformat(),
    }


def record_values(value):
    name = value.get("name", "")
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
        raise ContentError("name", "Enter a name up to 120 characters.")
    kind = value.get("kind")
    data = normalize_content(kind, value.get("data"))
    appearance = appearance_settings(value.get("appearance", {}))
    return {"name": name.strip(), "kind": kind, "data": data, "appearance": appearance}


@ensure_csrf_cookie
def app(request):
    return render(
        request,
        "qrapp/app.html",
        {"config": {"unlocked": unlocked(request), "schema": SCHEMA, "labels": LABELS}},
    )


@require_POST
@api
def unlock(request):
    if not consume(request, "login", 5) or not consume(request, "login-global", 2000, 3600, True):
        response = JsonResponse({"error": "Too many attempts. Try again in 15 minutes."}, status=429)
        response["Retry-After"] = "900"
        return response
    code = body(request).get("code")
    if not isinstance(code, str) or not hmac.compare_digest(code.encode(), settings.ACCESS_CODE.encode()):
        return JsonResponse({"error": "Incorrect code. Try again."}, status=403)
    request.session.flush()
    request.session["gate"] = {
        "version": digest("gate:" + settings.ACCESS_CODE),
        "expires": time.time() + 86400,
    }
    request.session.set_expiry(86400)
    return JsonResponse({"unlocked": True})


@require_POST
def lock(request):
    request.session.flush()
    return JsonResponse({"unlocked": False})


@private
@require_http_methods(["GET", "POST"])
@api
def records(request):
    if request.method == "GET":
        query = request.GET.get("search", "")[:120]
        rows = QRRecord.objects.filter(name__icontains=query).order_by("-created_at")
        page = Paginator(rows, 25).get_page(request.GET.get("page", 1))
        return JsonResponse(
            {
                "items": [serialized(r) for r in page],
                "page": page.number,
                "pages": page.paginator.num_pages,
                "count": page.paginator.count,
                "stats": {
                    "total": QRRecord.objects.count(),
                    "active": QRRecord.objects.filter(active=True).count(),
                    "opens": QRRecord.objects.aggregate(total=Sum("total_opens"))["total"] or 0,
                },
            }
        )
    if not consume(request, "create", 1000, 3600):
        return JsonResponse({"error": "Creation limit reached. Try later."}, status=429)
    row = QRRecord.objects.create(**record_values(body(request)))
    return JsonResponse(serialized(row), status=201)


@private
@require_http_methods(["GET", "PATCH", "DELETE"])
@api
def record(request, id):
    row = get_object_or_404(QRRecord, pk=id)
    if request.method == "DELETE":
        row.delete()
        return HttpResponse(status=204)
    if request.method == "PATCH":
        data = body(request)
        if set(data) == {"active"}:
            if type(data["active"]) is not bool:
                raise ValueError("Use on or off for active.")
            row.active = data["active"]
            row.save(update_fields=["active", "updated_at"])
        else:
            values = record_values(data)
            for key, value in values.items():
                setattr(row, key, value)
            row.save(update_fields=[*values, "updated_at"])
    return JsonResponse(serialized(row))


@require_POST
@api
def export(request):
    if not consume(request, "render", 120, 60):
        return JsonResponse({"error": "Too many requests. Try again in a minute."}, status=429)
    data = body(request)
    if data.get("id"):
        if not unlocked(request):
            return JsonResponse({"error": "Unlock the workspace."}, status=401)
        row = get_object_or_404(QRRecord, pk=data["id"])
        payload = settings.PUBLIC_BASE_URL + "/q/" + row.id + "/"
        appearance = row.appearance
    else:
        payload = build_payload(data.get("kind"), data.get("data"))
        appearance = data.get("appearance", {})
    fmt = data.get("format", "png")
    content = render_export(payload, appearance, fmt)
    response = HttpResponse(content, content_type="image/png" if fmt == "png" else "image/svg+xml")
    response["Content-Disposition"] = f'attachment; filename="qr.{fmt}"'
    return response


def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok", "revision": settings.SOURCE_REVISION})
