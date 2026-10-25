import hashlib
import hmac
import time
from datetime import datetime, timezone
from functools import wraps

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse

from .models import RateBucket


def digest(value):
    return hmac.new(settings.SECRET_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()


def unlocked(request):
    gate = request.session.get("gate", {})
    return (
        isinstance(gate, dict)
        and isinstance(gate.get("expires"), (int, float))
        and time.time() < gate["expires"]
        and hmac.compare_digest(str(gate.get("version", "")), digest("gate:" + settings.ACCESS_CODE))
    )


def private(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not unlocked(request):
            return JsonResponse({"error": "Unlock the workspace to continue."}, status=401)
        return view(request, *args, **kwargs)

    return wrapped


def consume(request, scope, limit, period=900, global_bucket=False):
    address = (
        "global"
        if global_bucket
        else (
            request.META.get("HTTP_X_REAL_IP", "")
            if settings.TRUST_PROXY
            else request.META.get("REMOTE_ADDR", "")
        )
    )
    window = int(time.time()) // period
    key = f"{scope}:{window}:" + digest(address)
    with transaction.atomic():
        bucket, _ = RateBucket.objects.get_or_create(
            key=key, defaults={"expires_at": datetime.fromtimestamp((window + 2) * period, timezone.utc)}
        )
        bucket = RateBucket.objects.select_for_update().get(pk=key)
        if bucket.count >= limit:
            return False
        bucket.count += 1
        bucket.save(update_fields=["count"])
    return True
