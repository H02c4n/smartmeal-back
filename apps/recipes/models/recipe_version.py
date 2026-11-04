import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.catalog.models import Product, UnitOfMeasure


class RecipeVersionStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    APPROVED = "APPROVED", "Approved"
    RETIRED = "RETIRED", "Retired"


class RecipeVersion(models.Model):
    """
    Bir ürünün belirli bir sürümü. Sürüm onaylandığında kilitlenir;
    değişiklik yeni sürüm oluşturur. Geçmiş sipariş/production kayıtları
    belirli bir sürüme referans verir.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="recipe_versions"
    )
    version_number = models.PositiveIntegerField()
    yield_quantity = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal("1")
    )
    yield_unit = models.ForeignKey(
        UnitOfMeasure, on_delete=models.PROTECT, related_name="recipe_yields"
    )
    status = models.CharField(
        max_length=16,
        choices=RecipeVersionStatus.choices,
        default=RecipeVersionStatus.DRAFT,
    )
    effective_from = models.DateTimeField(null=True, blank=True)
    effective_to = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_recipes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "recipes_recipe_version"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "version_number"],
                name="uniq_product_version",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product.sku} v{self.version_number} [{self.status}]"

    @property
    def is_locked(self) -> bool:
        """Onaylanmış veya emekli sürüm değiştirilemez."""
        return self.status in (RecipeVersionStatus.APPROVED, RecipeVersionStatus.RETIRED)

    def approve(self, user) -> None:
        """
        Sürümü onayla. Sadece DRAFT → APPROVED geçişine izin verilir.
        approved_by ve effective_from set edilir, kayıt kilitlenir.
        """
        if self.status != RecipeVersionStatus.DRAFT:
            raise ValidationError(
                f"Sadece DRAFT sürüm onaylanabilir. Mevcut durum: {self.status}."
            )
        if not user or not user.is_authenticated:
            raise ValidationError("Onay için geçerli bir kullanıcı gerekli.")

        self.status = RecipeVersionStatus.APPROVED
        self.approved_by = user
        self.effective_from = timezone.now()
        self.save(
            update_fields=["status", "approved_by", "effective_from", "updated_at"]
        )

    def save(self, *args, **kwargs):
        # Kilitli sürümün değiştirilmesini engelle (yalnızca güncelleme yolu).
        if not self._state.adding:
            db_obj = RecipeVersion.objects.filter(pk=self.pk).only("status").first()
            if db_obj and db_obj.status in (
                RecipeVersionStatus.APPROVED,
                RecipeVersionStatus.RETIRED,
            ):
                raise ValidationError(
                    "Onaylanmış veya emekli sürüm değiştirilemez. Yeni sürüm oluşturun."
                )
        super().save(*args, **kwargs)