from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from evaluations.models import EmployeeQuestionnaire
from scoring.models import (
    EmployeePerformanceScore,
    EmployeePastPerformanceIndex,
    EmployeePotentialScore,
    EmployeeNineBoxPlacement,
    EmployeeAppraisalRecommendation,
    EmployeeAnalyticsRelease,
)


class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if str(getattr(request.user, "employee_number", "")) != "100607":
            return Response({"error": "Not authorized"}, status=403)

        questionnaires = list(
            EmployeeQuestionnaire.objects.select_related("employee", "review_cycle").all()
        )

        total = len(questionnaires)

        all_statuses = [q.status for q in questionnaires]

        # -----------------------------
        # CUMULATIVE questionnaire progress counts
        # -----------------------------
        draft_count = sum(1 for status in all_statuses if status == "draft")

        self_submitted_count = sum(
            1 for status in all_statuses
            if status in [
                "self_submitted",
                "under_rm_review",
                "under_peer_review",
                "rm_reviewed",
                "under_skip_review",
                "skip_reviewed",
                "completed",
            ]
        )

        under_rm_review_count = sum(
            1 for status in all_statuses
            if status in [
                "under_rm_review",
                "under_peer_review",
                "rm_reviewed",
                "under_skip_review",
                "skip_reviewed",
                "completed",
            ]
        )

        under_skip_review_count = sum(
            1 for status in all_statuses
            if status in [
                "under_skip_review",
                "skip_reviewed",
                "completed",
            ]
        )

        completed_count = sum(
            1 for status in all_statuses
            if status == "completed"
        )

        # Parallel peer tracking is better shown separately
        peer_assigned_count = sum(
            1 for q in questionnaires if q.peer_reviewer_id is not None
        )

        # -----------------------------
        # Score engine progress
        # -----------------------------
        score_generated = EmployeePerformanceScore.objects.count()
        ppi_generated = EmployeePastPerformanceIndex.objects.count()
        potential_generated = EmployeePotentialScore.objects.count()
        ninebox_generated = EmployeeNineBoxPlacement.objects.count()
        appraisal_generated = EmployeeAppraisalRecommendation.objects.count()

        # -----------------------------
        # Fast lookup sets for analytics release readiness
        # -----------------------------
        score_q_ids = set(
            EmployeePerformanceScore.objects.values_list("employee_questionnaire_id", flat=True)
        )

        potential_q_ids = set(
            EmployeePotentialScore.objects.values_list("employee_questionnaire_id", flat=True)
        )

        ninebox_q_ids = set(
            EmployeeNineBoxPlacement.objects.values_list("employee_questionnaire_id", flat=True)
        )

        appraisal_q_ids = set(
            EmployeeAppraisalRecommendation.objects.values_list("employee_questionnaire_id", flat=True)
        )

        released_q_ids = set(
            EmployeeAnalyticsRelease.objects.filter(is_released_to_employee=True)
            .values_list("employee_questionnaire_id", flat=True)
        )

        # PPI is employee + review_cycle based
        ppi_pairs = set(
            EmployeePastPerformanceIndex.objects.values_list("employee_id", "review_cycle_id")
        )

        released_count = 0
        ready_not_released_count = 0
        not_ready_count = 0

        for questionnaire in questionnaires:
            questionnaire_id = questionnaire.id
            employee_id = questionnaire.employee_id
            review_cycle_id = questionnaire.review_cycle_id

            has_score = questionnaire_id in score_q_ids
            has_ppi = (employee_id, review_cycle_id) in ppi_pairs
            has_potential = questionnaire_id in potential_q_ids
            has_ninebox = questionnaire_id in ninebox_q_ids
            has_appraisal = questionnaire_id in appraisal_q_ids

            is_ready = all([
                has_score,
                has_ppi,
                has_potential,
                has_ninebox,
                has_appraisal,
            ])

            is_released = questionnaire_id in released_q_ids

            if is_released:
                released_count += 1
            elif is_ready:
                ready_not_released_count += 1
            else:
                not_ready_count += 1

        return Response({
            "questionnaire_progress": {
                "total": total,
                "draft": draft_count,
                "self_submitted": self_submitted_count,
                "under_rm_review": under_rm_review_count,
                "under_skip_review": under_skip_review_count,
                "peer_assigned": peer_assigned_count,
                "completed": completed_count,
            },
            "score_engine": {
                "scores_generated": score_generated,
                "ppi_generated": ppi_generated,
                "potential_generated": potential_generated,
                "ninebox_generated": ninebox_generated,
                "appraisal_generated": appraisal_generated,
            },
            "analytics_release": {
                "released": released_count,
                "ready_not_released": ready_not_released_count,
                "not_ready": not_ready_count,
            },
        })