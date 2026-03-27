from rest_framework import serializers

from evaluations.models import (
    QuestionCategory,
    QuestionParameter,
    ReviewCycle,
)

from scoring.models import (
    PotentialParameter,
    ScoreConfiguration,
    PotentialScoreConfiguration,
    AppraisalRecommendationConfig,
)


class QuestionCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionCategory
        fields = ["id", "name", "category_type"]


class QuestionParameterListSerializer(serializers.ModelSerializer):
    category = QuestionCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=QuestionCategory.objects.all(),
        source="category",
        write_only=True,
        required=False,
    )

    class Meta:
        model = QuestionParameter
        fields = [
            "id",
            "question_text",
            "category",
            "category_id",
            "department",
            "default_weightage",
            "is_active",
        ]


class QuestionParameterCreateUpdateSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=QuestionCategory.objects.all(),
        source="category",
    )

    class Meta:
        model = QuestionParameter
        fields = [
            "question_text",
            "category_id",
            "department",
            "default_weightage",
            "is_active",
        ]

class PotentialParameterListSerializer(serializers.ModelSerializer):
    class Meta:
        model = PotentialParameter
        fields = [
            "id",
            "question_text",
            "weightage",
            "is_active",
            "created_at",
        ]


class PotentialParameterCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PotentialParameter
        fields = [
            "question_text",
            "weightage",
            "is_active",
        ]

class ScoreConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoreConfiguration
        fields = [
            "id",
            "name",
            "behavioural_weight",
            "performance_weight",
            "self_weight",
            "rm_weight",
            "skip_weight",
            "peer_weight",
            "is_active",
            "created_at",
        ]


class PotentialScoreConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PotentialScoreConfiguration
        fields = [
            "id",
            "name",
            "rm_weight",
            "skip_weight",
            "is_active",
            "created_at",
        ]


class AppraisalRecommendationConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppraisalRecommendationConfig
        fields = [
            "id",
            "box_label",
            "min_percent",
            "max_percent",
            "is_active",
            "created_at",
            "updated_at",
        ]

class ReviewCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewCycle
        fields = [
            "id",
            "name",
            "start_date",
            "end_date",
            "is_active",
        ]