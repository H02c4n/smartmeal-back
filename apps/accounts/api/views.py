from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import LoginSerializer, UserSerializer


class LoginView(APIView):
    """
    Session login. CSRF muaf (henüz session yok). Başarılıysa session
    cookie set edilir, sonraki isteklerde `SessionAuthentication` çalışır.
    """
    permission_classes = [AllowAny]
    authentication_classes: list = []

    @method_decorator(csrf_exempt)
    def post(self, request):
        ser = LoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=ser.validated_data["email"],
            password=ser.validated_data["password"],
        )
        if user is None or not user.is_active:
            return Response(
                {"error": {"code": "AUTHENTICATION_FAILED",
                           "message": "Email veya şifre hatalı.",
                           "request_id": request.headers.get("X-Request-ID", "")}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        login(request, user)
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    """Session'ı sonlandırır. CSRF korumalı."""

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """Giriş yapmış kullanıcının bilgileri."""

    permission_classes = [IsAuthenticated]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response(UserSerializer(request.user).data)