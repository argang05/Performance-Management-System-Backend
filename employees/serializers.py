from rest_framework import serializers
from .models import Employee


class ManagerMiniSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for reporting/skip-level manager details.
    """

    full_name = serializers.ReadOnlyField()

    class Meta:
        model = Employee
        fields = [
            "id",
            "employee_number",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "department",
            "designation",
            "band",
        ]


class EmployeeListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for employee listing.
    """

    full_name = serializers.ReadOnlyField()
    experience_years = serializers.ReadOnlyField()
    reporting_manager_name = serializers.SerializerMethodField()
    skip_level_manager_name = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            "id",
            "employee_number",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "department",
            "designation",
            "old_designation",
            "old_bu",
            "band",
            "date_of_joining",
            "experience_years",
            "jd_file_url",
            "jd_mapping",
            "skill_matrix_mapping",
            "reporting_manager",
            "reporting_manager_name",
            "skip_level_manager",
            "skip_level_manager_name",
            "role",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def get_reporting_manager_name(self, obj):
        return obj.reporting_manager.full_name if obj.reporting_manager else None

    def get_skip_level_manager_name(self, obj):
        return obj.skip_level_manager.full_name if obj.skip_level_manager else None


class EmployeeCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for create/update employee.
    Password is write-only for security reasons.
    """

    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Employee
        fields = [
            "id",
            "employee_number",
            "password",
            "first_name",
            "last_name",
            "email",
            "department",
            "designation",
            "old_designation",
            "old_bu",
            "band",
            "date_of_joining",
            "jd_file_url",
            "jd_mapping",
            "skill_matrix_mapping",
            "reporting_manager",
            "skip_level_manager",
            "role",
            "is_active",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password", None)

        employee = Employee(**validated_data)

        if password:
            employee.set_password(password)
        else:
            raise serializers.ValidationError({"password": "Password is required."})

        employee.save()
        return employee

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance


class EmployeeMeSerializer(serializers.ModelSerializer):
    """
    Serializer for logged-in employee profile.
    """

    full_name = serializers.ReadOnlyField()
    experience_years = serializers.ReadOnlyField()

    reporting_manager = ManagerMiniSerializer(read_only=True)
    skip_level_manager = ManagerMiniSerializer(read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "employee_number",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "department",
            "designation",
            "old_designation",
            "old_bu",
            "band",
            "date_of_joining",
            "experience_years",
            "jd_file_url",
            "jd_mapping",
            "skill_matrix_mapping",
            "reporting_manager",
            "skip_level_manager",
            "role",
            "is_active",
        ]