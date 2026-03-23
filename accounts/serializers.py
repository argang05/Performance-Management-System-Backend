from rest_framework import serializers


class EmployeeLoginSerializer(serializers.Serializer):
    """
    Login serializer using employee_number and password.
    """

    employee_number = serializers.CharField()
    password = serializers.CharField(write_only=True)