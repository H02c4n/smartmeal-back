import uuid

from django.conf import settings
from django.db import models


class RoleCode(models.TextChoices):
    CUSTOMER = "CUSTOMER", "Customer"
    ADMIN = "ADMIN", "Admin"
    PLANNER = "PLANNER", "Planner"
    PURCHASING = "PURCHASING", "Purchasing"
    PRODUCTION = "PRODUCTION", "Production"
    QUALITY = "QUALITY", "Quality"
    PACKING = "PACKING", "Packing"
    DRIVER = "DRIVER", "Driver"
    SUPPORT = "SUPPORT", "Support"
    FINANCE = "FINANCE", "Finance"


class RoleAssignment(models.Model):
    """Bir kullanıcıya rol ataması. Aynı rol bir kez atanabilir."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    role_code = models.CharField(max_length=32, choices=RoleCode.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_role_assignment"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role_code"],
                name="uniq_user_role",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} — {self.role_code}"