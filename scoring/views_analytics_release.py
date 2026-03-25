from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from evaluations.models import EmployeeQuestionnaire
from scoring.services_analytics_release import (
    get_or_create_analytics_release,
    get_analytics_readiness,
    release_analytics_to_employee,
    unrelease_analytics_to_employee,
    build_employee_analytics_report,
)


def is_scoring_admin(user):
    return str(getattr(user, "employee_number", "")) == "100607"


class AnalyticsReleaseStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, questionnaire_id):
        if not is_scoring_admin(request.user):
            return Response(
                {"error": "You are not authorized to access analytics release status."},
                status=403
            )

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire.objects.select_related("employee", "review_cycle"),
            id=questionnaire_id
        )

        analytics_release = get_or_create_analytics_release(questionnaire)
        readiness = get_analytics_readiness(questionnaire)

        return Response({
            "questionnaire_id": questionnaire.id,
            "employee_name": getattr(questionnaire.employee, "full_name", None),
            "employee_number": getattr(questionnaire.employee, "employee_number", None),
            "review_cycle": getattr(questionnaire.review_cycle, "name", str(questionnaire.review_cycle)),

            "is_released_to_employee": analytics_release.is_released_to_employee,
            "released_at": analytics_release.released_at,
            "released_by": (
                getattr(analytics_release.released_by, "full_name", None)
                if analytics_release.released_by else None
            ),

            "is_ready": readiness["is_ready"],
            "missing_requirements": readiness["missing_requirements"],

            "has_processed_score": readiness["has_processed_score"],
            "has_ppi": readiness["has_ppi"],
            "has_potential": readiness["has_potential"],
            "has_nine_box": readiness["has_nine_box"],
            "has_self_feedback": readiness["has_self_feedback"],
            "has_rm_feedback": readiness["has_rm_feedback"],
            "has_skip_feedback": readiness["has_skip_feedback"],
            "has_peer_feedback": readiness["has_peer_feedback"],
        })


class AnalyticsReleaseToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, questionnaire_id):
        if not is_scoring_admin(request.user):
            return Response(
                {"error": "You are not authorized to release analytics data."},
                status=403
            )

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire,
            id=questionnaire_id
        )

        is_released_to_employee = request.data.get("is_released_to_employee")

        if is_released_to_employee is None:
            return Response(
                {"error": "is_released_to_employee is required."},
                status=400
            )

        if bool(is_released_to_employee):
            result = release_analytics_to_employee(questionnaire, request.user)
        else:
            result = unrelease_analytics_to_employee(questionnaire, request.user)

        if not result["success"]:
            return Response(
                {
                    "error": result["message"],
                    "missing_requirements": result.get("missing_requirements", []),
                },
                status=400
            )

        analytics_release = get_or_create_analytics_release(questionnaire)

        return Response({
            "message": result["message"],
            "questionnaire_id": questionnaire.id,
            "is_released_to_employee": analytics_release.is_released_to_employee,
            "released_at": analytics_release.released_at,
            "unreleased_at": analytics_release.unreleased_at,
        })


class MyAnalyticsReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, questionnaire_id):
        questionnaire = get_object_or_404(
            EmployeeQuestionnaire.objects.select_related("employee", "review_cycle"),
            id=questionnaire_id
        )

        if questionnaire.employee_id != request.user.id:
            return Response(
                {"error": "You are not authorized to view this analytics report."},
                status=403
            )

        analytics_release = get_or_create_analytics_release(questionnaire)

        if not analytics_release.is_released_to_employee:
            return Response(
                {"message": "Analytics report has not been released yet."},
                status=403
            )

        report = build_employee_analytics_report(questionnaire)
        return Response(report)