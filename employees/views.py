import os
from urllib.parse import urlparse

from supabase import create_client, Client

from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, permissions
from .models import Employee
from .serializers import EmployeeListSerializer, EmployeeCreateUpdateSerializer

def get_supabase_client() -> Client:
    supabase_url = os.getenv("SUPABASE_URL") or getattr(settings, "SUPABASE_URL", None)
    supabase_key = os.getenv("SUPABASE_KEY") or getattr(settings, "SUPABASE_KEY", None)

    if not supabase_url or not supabase_key:
        raise ValueError("Supabase credentials are not configured properly.")

    return create_client(supabase_url, supabase_key)


def extract_supabase_object_path(file_url: str, bucket_name: str) -> str | None:
    """
    Extract object path from a public Supabase storage URL.
    Example:
    .../storage/v1/object/public/jd-files/100093/job_description.pdf
    -> 100093/job_description.pdf
    """
    if not file_url:
        return None

    try:
        parsed = urlparse(file_url)
        marker = f"/storage/v1/object/public/{bucket_name}/"
        if marker in parsed.path:
            return parsed.path.split(marker, 1)[1]
    except Exception:
        return None

    return None


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

class EmployeeJDUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        employee: Employee = request.user
        uploaded_file = request.FILES.get("file")
        bucket_name = "jd-files"

        if not uploaded_file:
            return Response({"error": "No file provided."}, status=400)

        if not uploaded_file.name.lower().endswith(".pdf"):
            return Response({"error": "Only PDF files are allowed."}, status=400)

        max_size_mb = 10
        if uploaded_file.size > max_size_mb * 1024 * 1024:
            return Response(
                {"error": f"File size must be less than {max_size_mb} MB."},
                status=400,
            )

        try:
            supabase = get_supabase_client()

            # Fixed path per employee -> safe overwrite, no duplicate file buildup
            object_path = f"{employee.employee_number}/job_description.pdf"

            old_url = employee.jd_file_url
            old_object_path = extract_supabase_object_path(old_url, bucket_name)

            file_bytes = uploaded_file.read()

            upload_response = supabase.storage.from_(bucket_name).upload(
                path=object_path,
                file=file_bytes,
                file_options={
                    "content-type": "application/pdf",
                    "upsert": "true",
                },
            )

            # Some supabase client versions return dict-like response, some object-like.
            # We mainly rely on exceptions; still keeping a sanity check.
            if upload_response is None:
                return Response({"error": "Upload failed."}, status=500)

            public_url = supabase.storage.from_(bucket_name).get_public_url(object_path)

            employee.jd_file_url = public_url

            # Future-ready metadata
            employee.jd_mapping = {
                **(employee.jd_mapping or {}),
                "storage_bucket": bucket_name,
                "storage_path": object_path,
                "original_filename": uploaded_file.name,
                "content_type": "application/pdf",
                "file_size_bytes": uploaded_file.size,
            }
            employee.save(update_fields=["jd_file_url", "jd_mapping", "updated_at"])

            # Optional cleanup for legacy old path only if different from new fixed path
            if old_object_path and old_object_path != object_path:
                try:
                    supabase.storage.from_(bucket_name).remove([old_object_path])
                except Exception:
                    # Ignore cleanup failure to avoid breaking successful upload flow
                    pass

            return Response(
                {
                    "message": "JD uploaded successfully.",
                    "jd_file_url": public_url,
                },
                status=200,
            )

        except Exception as e:
            return Response(
                {"error": f"Failed to upload JD file. {str(e)}"},
                status=500,
            )