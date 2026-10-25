import secrets
from django.db import models


def public_id():
    return secrets.token_urlsafe(16)


class QRRecord(models.Model):
    id = models.CharField(primary_key=True, max_length=32, default=public_id, editable=False)
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=16)
    data = models.JSONField()
    appearance = models.JSONField(default=dict)
    active = models.BooleanField(default=True)
    total_opens = models.PositiveBigIntegerField(default=0)
    last_opened_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class RateBucket(models.Model):
    key = models.CharField(primary_key=True, max_length=100)
    count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)
