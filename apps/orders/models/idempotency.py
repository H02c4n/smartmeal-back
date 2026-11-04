import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


def default_idempotency_expiry():
    return timezone.now() + timezone.timedelta(hours=24)


class IdempotencyRecord(models.Model):
    """
    Idempotency-Key header'ı ile gelen isteklerin sonuçlarını saklar.
    Aynı (actor, key) + aynı request_hash → aynı response döner.
    Aynı key + farklı request_hash → 422 IDEMPOTENCY_CONFLICT.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="idempotency_records"
    )
    key = models.CharField(max_length=128)
    request_hash = models.CharField(max_length=64)
    response_status = models.PositiveIntegerField()
    response_body = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_idempotency_expiry)

    class Meta:
        db_table = "orders_idempotency_record"
        constraints = [
            models.UniqueConstraint(
                fields=["actor", "key"], name="uniq_actor_idempotency_key"
            ),
        ]
        indexes = [
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.actor_id}:{self.key}"