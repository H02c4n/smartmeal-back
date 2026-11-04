from rest_framework import serializers

from apps.accounts.models import User


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "phone", "is_staff", "roles"]
        read_only_fields = fields

    def get_roles(self, obj) -> list[str]:
        return list(obj.role_assignments.values_list("role_code", flat=True))