from rest_framework import serializers
from .models import EmployeePerformanceScore


class EmployeePerformanceScoreSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmployeePerformanceScore
        fields = "__all__"


class HRScoreOverrideSerializer(serializers.Serializer):
    hr_override_score = serializers.FloatField()
    override_reason = serializers.CharField()


class ReleaseScoreSerializer(serializers.Serializer):
    is_released_to_employee = serializers.BooleanField()