from apps.common.pagination import CreatedAtCursorPagination
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin

from apps.orders.models import Order, OrderStatus
from apps.orders.services.fulfillment import cancel_order, confirm_order
from apps.orders.services.idempotency import check_idempotency, save_idempotency
from apps.orders.services.order import create_order

from .permissions import IsOwnerOrStaff, IsStaff
from .serializers import OrderCreateSerializer, OrderSerializer


class OrderViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """
    Sipariş listeleme/oluşturma/iptal/onaylama.
    - List/detail: kullanıcı kendi siparişlerini görür; staff hepsini.
    - Create: authenticated kullanıcı; Idempotency-Key destekli.
    - Cancel: sahip veya staff.
    - Confirm: yalnızca staff.
    """

    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CreatedAtCursorPagination

    def get_queryset(self):
        qs = Order.objects.select_related("customer").prefetch_related("lines")

        # Staff olmayan sadece kendi siparişini görür
        if not self.request.user.is_staff:
            return qs.filter(customer=self.request.user)

        # Staff için filtre desteği
        status = self.request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)

        search = self.request.query_params.get("search")
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(order_number__icontains=search)
                | Q(customer__email__icontains=search)
            )

        return qs

    def get_permissions(self):
        if self.action == "confirm":
            return [IsAuthenticated(), IsStaff()]
        if self.action in ("cancel",):
            return [IsAuthenticated(), IsOwnerOrStaff()]
        return [IsAuthenticated()]

    def create(self, request):
        ser = OrderCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        idem_key = request.headers.get("Idempotency-Key", "").strip()

        # Aynı key + aynı body → aynı response
        existing, conflict = check_idempotency(idem_key, request.user, ser.validated_data)
        if conflict:
            return Response(
                {"error": {"code": "IDEMPOTENCY_CONFLICT",
                           "message": "Aynı Idempotency-Key farklı bir istek için kullanıldı."}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if existing:
            return Response(existing.response_body, status=existing.response_status)

        try:
            order = create_order(
                customer=request.user,
                delivery_date=ser.validated_data["delivery_date"],
                delivery_address=ser.validated_data["delivery_address"],
                items=[
                    {"product_id": str(i["product_id"]), "quantity": i["quantity"]}
                    for i in ser.validated_data["items"]
                ],
                notes=ser.validated_data.get("notes", ""),
            )
        except ValueError as e:
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = OrderSerializer(order).data
        save_idempotency(
            key=idem_key,
            actor=request.user,
            request_body=ser.validated_data,
            response_status=201,
            response_body=payload,
        )
        return Response(payload, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = self.get_object()
        reason = request.data.get("reason", "")
        try:
            cancel_order(order_id=order.id, reason=reason, actor=request.user)
        except ValueError as e:
            return Response(
                {"error": {"code": "INVALID_STATE_TRANSITION", "message": str(e)}},
                status=status.HTTP_409_CONFLICT,
            )
        order.refresh_from_db()
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        order = self.get_object()
        try:
            confirm_order(order_id=order.id, actor=request.user)
        except ValueError as e:
            return Response(
                {"error": {"code": "INVALID_STATE_TRANSITION", "message": str(e)}},
                status=status.HTTP_409_CONFLICT,
            )
        order.refresh_from_db()
        return Response(OrderSerializer(order).data)