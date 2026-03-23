from rest_framework import generics, permissions
from .models import Employee
from .serializers import EmployeeListSerializer, EmployeeCreateUpdateSerializer


class EmployeeListCreateView(generics.ListCreateAPIView):
    """
    GET  -> list all employees
    POST -> create a new employee

    For now:
    - Any authenticated user can access this endpoint.
    Later:
    - Restrict create/list access based on role (HR/Admin/Manager).
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Base queryset with manager relations preloaded for performance.
        Later this can be extended with filters like:
        - department
        - designation
        - employee_number
        - reporting_manager
        """
        return Employee.objects.select_related(
            "reporting_manager",
            "skip_level_manager"
        ).all()

    def get_serializer_class(self):
        """
        Use create/update serializer for POST
        and list serializer for GET.
        """
        if self.request.method == "POST":
            return EmployeeCreateUpdateSerializer
        return EmployeeListSerializer


class EmployeeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    -> employee details
    PUT    -> full update
    PATCH  -> partial update
    DELETE -> remove employee

    For now:
    - Any authenticated user can access this endpoint.
    Later:
    - Restrict update/delete access based on role and ownership rules.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Preload related manager fields for better query performance.
        """
        return Employee.objects.select_related(
            "reporting_manager",
            "skip_level_manager"
        ).all()

    def get_serializer_class(self):
        """
        Use read serializer for GET
        and write serializer for update operations.
        """
        if self.request.method == "GET":
            return EmployeeListSerializer
        return EmployeeCreateUpdateSerializer