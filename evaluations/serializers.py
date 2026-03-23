from rest_framework import serializers
from .models import *


class QuestionnaireItemSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source="parameter.question_text")
    category = serializers.CharField(source="parameter.category.name")
    category_type = serializers.CharField(source="parameter.category.category_type")

    class Meta:
        model = EmployeeQuestionnaireItem
        fields = [
            "id",
            "question_text",
            "category",
            "category_type",
            "weightage",
            "order",
        ]


class QuestionnaireResponseSerializer(serializers.Serializer):

    item_id = serializers.IntegerField()
    score = serializers.IntegerField()