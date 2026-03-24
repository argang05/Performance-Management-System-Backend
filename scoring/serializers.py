from rest_framework import serializers
from .models import EmployeePerformanceScore


class EmployeePerformanceScoreSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmployeePerformanceScore
        fields = "__all__"