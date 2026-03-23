from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken

from employees.models import Employee
from employees.serializers import EmployeeMeSerializer
from .serializers import EmployeeLoginSerializer


class EmployeeLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = EmployeeLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        employee_number = serializer.validated_data["employee_number"]
        password = serializer.validated_data["password"]

        user = authenticate(
            request=request,
            employee_number=employee_number,
            password=password
        )

        if not user:
            return Response(
                {"detail": "Invalid employee number or password."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return Response(
                {"detail": "This employee account is inactive."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Refetch with related managers for cleaner nested serialization
        user = Employee.objects.select_related(
            "reporting_manager",
            "skip_level_manager"
        ).get(pk=user.pk)

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Login successful.",
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "employee": EmployeeMeSerializer(user).data
            },
            status=status.HTTP_200_OK
        )


class EmployeeMeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = Employee.objects.select_related(
            "reporting_manager",
            "skip_level_manager"
        ).get(pk=request.user.pk)

        serializer = EmployeeMeSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)