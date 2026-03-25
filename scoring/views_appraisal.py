from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from evaluations.models import EmployeeQuestionnaire
from scoring.models import EmployeeAppraisalRecommendation
from scoring.service_appraisal_engine import (
    generate_appraisal_recommendation,
    get_appraisal_recommendation,
    apply_hr_override,
)


def is_scoring_admin(user):
    return str(getattr(user, "employee_number", "")) == "100607"


class GenerateAppraisalRecommendationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, questionnaire_id):
        if not is_scoring_admin(request.user):
            return Response(
                {"error": "You are not authorized to generate appraisal recommendation."},
                status=403
            )

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire.objects.select_related("employee", "review_cycle"),
            id=questionnaire_id
        )

        recommendation = generate_appraisal_recommendation(questionnaire)

        return Response({
            "message": "Appraisal recommendation generated successfully.",
            "questionnaire_id": questionnaire.id,
            "employee_name": questionnaire.employee.full_name,
            "employee_number": questionnaire.employee.employee_number,
            "review_cycle": questionnaire.review_cycle.name if questionnaire.review_cycle else None,

            "box_label": recommendation.box_label,
            "ppi_score_used": recommendation.ppi_score_used,
            "potential_score_used": recommendation.potential_score_used,

            "min_appraisal_percent": recommendation.min_appraisal_percent,
            "max_appraisal_percent": recommendation.max_appraisal_percent,
            "suggested_appraisal_percent": recommendation.suggested_appraisal_percent,

            "hr_override_percent": recommendation.hr_override_percent,
            "override_reason": recommendation.override_reason,
            "final_effective_appraisal_percent": recommendation.final_effective_appraisal_percent,

            "calculated_at": recommendation.calculated_at,
        })


class AppraisalRecommendationResultView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, questionnaire_id):
        if not is_scoring_admin(request.user):
            return Response(
                {"error": "You are not authorized to view appraisal recommendation."},
                status=403
            )

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire.objects.select_related("employee", "review_cycle"),
            id=questionnaire_id
        )

        recommendation = get_appraisal_recommendation(questionnaire)

        return Response({
            "questionnaire_id": questionnaire.id,
            "employee_name": questionnaire.employee.full_name,
            "employee_number": questionnaire.employee.employee_number,
            "review_cycle": questionnaire.review_cycle.name if questionnaire.review_cycle else None,

            "box_label": recommendation.box_label,
            "ppi_score_used": recommendation.ppi_score_used,
            "potential_score_used": recommendation.potential_score_used,

            "min_appraisal_percent": recommendation.min_appraisal_percent,
            "max_appraisal_percent": recommendation.max_appraisal_percent,
            "suggested_appraisal_percent": recommendation.suggested_appraisal_percent,

            "hr_override_percent": recommendation.hr_override_percent,
            "override_reason": recommendation.override_reason,
            "final_effective_appraisal_percent": recommendation.final_effective_appraisal_percent,

            "overridden_by": (
                recommendation.overridden_by.full_name
                if recommendation.overridden_by else None
            ),
            "overridden_at": recommendation.overridden_at,
            "calculated_at": recommendation.calculated_at,
        })


class AppraisalRecommendationOverrideView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, questionnaire_id):
        if not is_scoring_admin(request.user):
            return Response(
                {"error": "You are not authorized to override appraisal recommendation."},
                status=403
            )

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire,
            id=questionnaire_id
        )

        recommendation = get_object_or_404(
            EmployeeAppraisalRecommendation,
            employee_questionnaire=questionnaire
        )

        override_percent = request.data.get("hr_override_percent")
        override_reason = request.data.get("override_reason")

        if override_percent in [None, ""]:
            return Response(
                {"error": "hr_override_percent is required."},
                status=400
            )

        if not override_reason or not str(override_reason).strip():
            return Response(
                {"error": "override_reason is required."},
                status=400
            )

        try:
            override_percent = round(float(override_percent), 2)
        except (ValueError, TypeError):
            return Response(
                {"error": "hr_override_percent must be a valid number."},
                status=400
            )

        recommendation = apply_hr_override(
            recommendation=recommendation,
            override_percent=override_percent,
            reason=override_reason.strip(),
            hr_employee=request.user
        )

        return Response({
            "message": "Appraisal override applied successfully.",
            "questionnaire_id": questionnaire.id,
            "box_label": recommendation.box_label,

            "suggested_appraisal_percent": recommendation.suggested_appraisal_percent,
            "hr_override_percent": recommendation.hr_override_percent,
            "override_reason": recommendation.override_reason,
            "final_effective_appraisal_percent": recommendation.final_effective_appraisal_percent,

            "overridden_by": (
                recommendation.overridden_by.full_name
                if recommendation.overridden_by else None
            ),
            "overridden_at": recommendation.overridden_at,
        })