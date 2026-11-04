from rest_framework.permissions import BasePermission


class IsOwnerOrStaff(BasePermission):
    """Nesnenin sahibi (customer) veya staff erişebilir."""

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return getattr(obj, "customer_id", None) == request.user.id


class IsStaff(BasePermission):
    """Sadece personel."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)