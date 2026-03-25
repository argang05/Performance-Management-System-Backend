from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from evaluations.models import EmployeeQuestionnaire

from .models import (
    EmployeePastPerformanceIndex,
    EmployeePotentialScore,
    EmployeeNineBoxPlacement,
)
from .services_ninebox import save_nine_box_placement


def is_scoring_admin(user):
    return str(getattr(user, "employee_number", "")) == "100607"


class GenerateNineBoxPlacementView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, questionnaire_id):
        if not is_scoring_admin(request.user):
            return Response(
                {"error": "You are not authorized to generate 9-box placement."},
                status=403
            )

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire.objects.select_related("employee", "review_cycle"),
            id=questionnaire_id
        )

        ppi_obj = get_object_or_404(
            EmployeePastPerformanceIndex,
            employee=questionnaire.employee,
            review_cycle=questionnaire.review_cycle
        )

        potential_obj = get_object_or_404(
            EmployeePotentialScore,
            employee=questionnaire.employee,
            review_cycle=questionnaire.review_cycle,
            employee_questionnaire=questionnaire
        )

        if ppi_obj.ppi_score is None:
            return Response(
                {"error": "PPI score is not available for this employee and cycle."},
                status=400
            )

        if potential_obj.final_potential_score is None:
            return Response(
                {"error": "Potential score is not available for this employee and cycle."},
                status=400
            )

        placement = save_nine_box_placement(
            employee=questionnaire.employee,
            review_cycle=questionnaire.review_cycle,
            employee_questionnaire=questionnaire,
            ppi_score=ppi_obj.ppi_score,
            potential_score=potential_obj.final_potential_score,
        )

        return Response({
            "message": "9-box placement generated successfully.",
            "questionnaire_id": questionnaire.id,
            "employee_name": questionnaire.employee.full_name,
            "employee_number": questionnaire.employee.employee_number,
            "review_cycle": questionnaire.review_cycle.name if questionnaire.review_cycle else None,
            "ppi_score": placement.ppi_score,
            "potential_score": placement.potential_score,
            "performance_bucket": placement.performance_bucket,
            "potential_bucket": placement.potential_bucket,
            "box_label": placement.box_label,
            "box_description": placement.box_description,
            "generated_at": placement.generated_at,
        })


class NineBoxPlacementResultView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, questionnaire_id):
        if not is_scoring_admin(request.user):
            return Response(
                {"error": "You are not authorized to view 9-box placement."},
                status=403
            )

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire.objects.select_related("employee", "review_cycle"),
            id=questionnaire_id
        )

        placement = get_object_or_404(
            EmployeeNineBoxPlacement,
            employee_questionnaire=questionnaire
        )

        return Response({
            "questionnaire_id": questionnaire.id,
            "employee_name": questionnaire.employee.full_name,
            "employee_number": questionnaire.employee.employee_number,
            "review_cycle": questionnaire.review_cycle.name if questionnaire.review_cycle else None,
            "ppi_score": placement.ppi_score,
            "potential_score": placement.potential_score,
            "performance_bucket": placement.performance_bucket,
            "potential_bucket": placement.potential_bucket,
            "box_label": placement.box_label,
            "box_description": placement.box_description,
            "generated_at": placement.generated_at,
        })