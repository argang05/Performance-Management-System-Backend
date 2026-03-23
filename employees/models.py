from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone


class EmployeeManager(BaseUserManager):
    def create_user(self, employee_number, password=None, **extra_fields):
        if not employee_number:
            raise ValueError("Employee number is required.")

        employee_number = str(employee_number).strip()
        user = self.model(employee_number=employee_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, employee_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(employee_number, password, **extra_fields)


class Employee(AbstractBaseUser, PermissionsMixin):
    # -----------------------------
    # Core identity fields
    # -----------------------------
    employee_number = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)

    # -----------------------------
    # Employee master fields
    # -----------------------------
    department = models.CharField(max_length=150, blank=True, null=True)
    designation = models.CharField(max_length=150, blank=True, null=True)
    old_designation = models.CharField(max_length=150, blank=True, null=True)
    old_bu = models.CharField(max_length=150, blank=True, null=True)
    band = models.CharField(max_length=50, blank=True, null=True)
    date_of_joining = models.DateField(blank=True, null=True)

    # -----------------------------
    # Future-ready structured fields
    # These remain nullable/blank for now.
    # Later these can store processed mapping results.
    # -----------------------------
    jd_mapping = models.JSONField(
        blank=True,
        null=True,
        help_text="Future-ready field to store JD mapping metadata, extracted keywords, matched competencies, etc."
    )

    skill_matrix_mapping = models.JSONField(
        blank=True,
        null=True,
        help_text="Future-ready field to store employee skill matrix mapping, proficiency alignment, and related metadata."
    )

    # Optional JD file URL from Supabase
    jd_file_url = models.URLField(blank=True, null=True)

    # -----------------------------
    # Manager hierarchy
    # -----------------------------
    reporting_manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reportees"
    )

    skip_level_manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="skip_level_reportees"
    )

    # -----------------------------
    # Status / permission fields
    # -----------------------------
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    role = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Optional field for future HR/admin/manager role expansion."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EmployeeManager()

    USERNAME_FIELD = "employee_number"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "employees"
        ordering = ["employee_number"]

    def __str__(self):
        return f"{self.employee_number} - {self.first_name} {self.last_name or ''}".strip()

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name or ''}".strip()

    @property
    def experience_years(self):
        if not self.date_of_joining:
            return None

        today = timezone.now().date()
        delta_days = (today - self.date_of_joining).days
        return round(delta_days / 365.25, 2)