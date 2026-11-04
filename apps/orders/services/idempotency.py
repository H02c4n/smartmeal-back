"""
Idempotency-Key header desteği. Basit yaklaşım:
- Aynı (actor, key) + aynı request_hash → kaydedilen response döner
- Aynı (actor, key) + farklı request_hash → IDEMPOTENCY_CONFLICT (422)
- Kayıt yoksa: caller devam eder, sonucu `save_idempotency()` ile saklar
"""
import hashlib
import json

from apps.orders.models import IdempotencyRecord

def _json_safe(obj):
    """
    DRF serializer çıktısındaki UUID, Decimal, date gibi değerleri
    JSON-safe hale getirir. Round-trip (dumps+loads) en güvenli yol:
    hangi alanın hangi tipi döndürdüğünü tek tek avlamaya gerek kalmaz.
    """
    return json.loads(json.dumps(obj, default=str, ensure_ascii=False))

def _hash_request(body: dict) -> str:
    """Deterministic hash — key sırası önemsiz."""
    canonical = json.dumps(body, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def check_idempotency(key: str, actor, request_body: dict):
    """
    Döndürülen: (record_or_None, conflict_bool)
    - record varsa ve hash eşleşiyorsa: (record, False) → aynı response dön
    - record varsa ama hash farklı: (None, True) → 422
    - record yoksa: (None, False) → yeni istek
    """
    if not key or not actor or not actor.is_authenticated:
        return None, False

    req_hash = _hash_request(request_body)
    try:
        record = IdempotencyRecord.objects.get(actor=actor, key=key)
    except IdempotencyRecord.DoesNotExist:
        return None, False

    if record.request_hash != req_hash:
        return None, True
    return record, False


def save_idempotency(
    *, key: str, actor, request_body: dict, response_status: int, response_body: dict
) -> None:
    """Başarılı create sonrası çağrılır. Best-effort; çakışırsa hata yutulur."""
    if not key or not actor or not actor.is_authenticated:
        return
    IdempotencyRecord.objects.update_or_create(
        actor=actor,
        key=key,
        defaults={
            "request_hash": _hash_request(request_body),
            "response_status": response_status,
            "response_body": _json_safe(response_body),
        },
    )