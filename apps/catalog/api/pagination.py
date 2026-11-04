from rest_framework.pagination import CursorPagination


class StandardCursorPagination(CursorPagination):
    """
    Cursor-based pagination. Cursor sıralaması -created_at ile
    (yeni kayıtlar önce). Page size global ayardan gelir.
    """
    ordering = "-created_at"