"""Paylaşılan cursor pagination sınıfları. Her modelin sıralama alanı farklı
olduğu için her alan için ayrı bir sınıf tutulur."""
from rest_framework.pagination import CursorPagination


class CreatedAtCursorPagination(CursorPagination):
    """created_at alanına sahip modeller için (catalog, inventory_lot)."""
    ordering = "-created_at"


class OccurredAtCursorPagination(CursorPagination):
    """occurred_at alanına sahip modeller için (stock_movement)."""
    ordering = "-occurred_at"


class ReceivedAtCursorPagination(CursorPagination):
    """received_at alanına sahip modeller için (order, delivery)."""
    ordering = "-received_at"