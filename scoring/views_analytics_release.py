from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from scoring.models import EmployeeAnalyticsRelease, EmployeeNineBoxPlacement, EmployeePastPerformanceIndex, EmployeePerformanceScore, EmployeePotentialScore
from evaluations.models import EmployeeQuestionnaire, EmployeeQuestionnaireStageSubmission
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

        # employee can only view their own analytics
        if questionnaire.employee_id != request.user.id:
            return Response(
                {"error": "You are not allowed to view this analytics report."},
                status=403
            )

        release_obj = EmployeeAnalyticsRelease.objects.filter(
            employee_questionnaire=questionnaire
        ).first()

        if not release_obj or not release_obj.is_released_to_employee:
            return Response(
                {"error": "Analytics report has not been released yet."},
                status=403
            )

        performance_score = EmployeePerformanceScore.objects.filter(
            employee_questionnaire=questionnaire
        ).first()

        ppi = EmployeePastPerformanceIndex.objects.filter(
            employee=questionnaire.employee,
            review_cycle=questionnaire.review_cycle
        ).first()

        potential = EmployeePotentialScore.objects.filter(
            employee_questionnaire=questionnaire
        ).first()

        nine_box = EmployeeNineBoxPlacement.objects.filter(
            employee_questionnaire=questionnaire
        ).first()

        feedback_sections = []

        submissions = EmployeeQuestionnaireStageSubmission.objects.filter(
            employee_questionnaire=questionnaire,
            evaluator_type__in=["self", "rm", "skip", "peer"],
            status="submitted"
        ).select_related("submitted_by")

        role_map = {
            "self": "Self",
            "rm": "Reporting Manager",
            "skip": "Skip-Level Manager",
            "peer": "Peer Reviewer",
        }

        for submission in submissions:
            feedback_sections.append({
                "role": role_map.get(submission.evaluator_type, submission.evaluator_type),
                "evaluator_name": (
                    submission.submitted_by.full_name
                    if submission.submitted_by and getattr(submission.submitted_by, "full_name", None)
                    else "—"
                ),
                "feedback": submission.feedback,
                "scope_of_improvement": submission.scope_of_improvement,
                "submitted_at": submission.submitted_at,
            })

        return Response({
            "employee_name": questionnaire.employee.full_name,
            "employee_number": questionnaire.employee.employee_number,
            "review_cycle": questionnaire.review_cycle.name if questionnaire.review_cycle else None,

            "performance_score": {
                "system_final_score": performance_score.system_final_score if performance_score else None,
                "hr_override_score": performance_score.hr_override_score if performance_score else None,
                "final_effective_score": performance_score.final_effective_score if performance_score else None,
            } if performance_score and release_obj.show_performance_score else None,

            "ppi": {
                "ppi_score": ppi.ppi_score if ppi else None,
            } if ppi and release_obj.show_ppi else None,

            "potential": {
                "final_potential_score": potential.final_potential_score if potential else None,
            } if potential and release_obj.show_potential_score else None,

            "nine_box": {
                "ppi_score": nine_box.ppi_score if nine_box else None,
                "potential_score": nine_box.potential_score if nine_box else None,
                "performance_bucket": nine_box.performance_bucket if nine_box else None,
                "potential_bucket": nine_box.potential_bucket if nine_box else None,
                "box_label": nine_box.box_label if nine_box else None,
                "box_description": nine_box.box_description if nine_box else None,
            } if nine_box and release_obj.show_nine_box else None,

            "feedback_sections": feedback_sections,
        })