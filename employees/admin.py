from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Employee


@admin.register(Employee)
class EmployeeAdmin(UserAdmin):
    model = Employee

    list_display = (
        "employee_number",
        "first_name",
        "last_name",
        "email",
        "department",
        "designation",
        "reporting_manager",
        "skip_level_manager",
        "is_active",
        "is_staff",
    )

    search_fields = ("employee_number", "first_name", "last_name", "email", "department")
    ordering = ("employee_number",)

    fieldsets = (
        ("Login Info", {
            "fields": ("employee_number", "password")
        }),
        ("Personal Info", {
            "fields": ("first_name", "last_name", "email")
        }),
        ("Employment Info", {
            "fields": (
                "department",
                "designation",
                "old_designation",
                "old_bu",
                "band",
                "date_of_joining",
                "future_field",
                "jd_file_url",
                "role",
            )
        }),
        ("Reporting Hierarchy", {
            "fields": ("reporting_manager", "skip_level_manager")
        }),
        ("Permissions", {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")
        }),
        ("Important Dates", {
            "fields": ("last_login",)
        }),
    )

    add_fieldsets = (
        ("Create Employee", {
            "classes": ("wide",),
            "fields": (
                "employee_number",
                "password1",
                "password2",
                "first_name",
                "last_name",
                "email",
                "is_active",
                "is_staff",
            ),
        }),
    )