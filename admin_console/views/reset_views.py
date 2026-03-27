from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction

from django.db.models import Count

from employees.models import Employee
from evaluations.models import (
    EmployeeQuestionnaire,
    EmployeeQuestionnaireItem,
    EmployeeQuestionnaireStageSubmission,
    EmployeeQuestionnaireResponse,
    ReviewCycle,
)

from scoring.models import (
    EmployeePerformanceScore,
    EmployeePastPerformanceIndex,
    EmployeePotentialAssessment,
    EmployeePotentialResponse,
    EmployeePotentialScore,
    EmployeeNineBoxPlacement,
    EmployeeAppraisalRecommendation,
    EmployeeAnalyticsRelease,
)

from evaluations.models import ReviewCycle


class EmployeeResetPreviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        # 🔐 ADMIN CHECK
        if str(getattr(request.user, "employee_number", "")) != "100607":
            return Response({"error": "Not authorized"}, status=403)

        employee_number = request.GET.get("employee_number")
        review_cycle_id = request.GET.get("review_cycle_id")
        scope = request.GET.get("scope")  # "cycle" or "all"

        if not employee_number:
            return Response({"error": "employee_number is required"}, status=400)

        # 🔍 GET EMPLOYEE
        employee = Employee.objects.filter(employee_number=employee_number).first()

        if not employee:
            return Response({"error": "Employee not found"}, status=404)

        # 📦 BASE RESPONSE
        response_data = {
            "employee": {
                "id": employee.id,
                "employee_number": employee.employee_number,
                "full_name": getattr(employee, "full_name", str(employee)),
                "department": getattr(employee, "department", None),
            },
            "review_cycle": None,
            "questionnaire": None,
            "delete_summary": {},
            "safe_to_reset": False,
            "warnings": [],
        }

        # =========================
        # MODE: CYCLE RESET
        # =========================
        if scope != "all":

            if not review_cycle_id:
                return Response({"error": "review_cycle_id is required for cycle reset"}, status=400)

            cycle = ReviewCycle.objects.filter(id=review_cycle_id).first()

            if not cycle:
                return Response({"error": "Invalid review cycle"}, status=404)

            response_data["review_cycle"] = {
                "id": cycle.id,
                "name": cycle.name,
            }

            questionnaire = EmployeeQuestionnaire.objects.filter(
                employee=employee,
                review_cycle=cycle
            ).first()

            if questionnaire:
                response_data["questionnaire"] = {
                    "id": questionnaire.id,
                    "status": questionnaire.status,
                    "submitted_at": questionnaire.submitted_at,
                }

            # =========================
            # COUNT DATA
            # =========================

            questionnaire_ids = EmployeeQuestionnaire.objects.filter(
                employee=employee,
                review_cycle=cycle
            ).values_list("id", flat=True)

            summary = {
                "questionnaires": EmployeeQuestionnaire.objects.filter(
                    id__in=questionnaire_ids
                ).count(),

                "questionnaire_items": EmployeeQuestionnaireItem.objects.filter(
                    employee_questionnaire_id__in=questionnaire_ids
                ).count(),

                "stage_submissions": EmployeeQuestionnaireStageSubmission.objects.filter(
                    employee_questionnaire_id__in=questionnaire_ids
                ).count(),

                "questionnaire_responses": EmployeeQuestionnaireResponse.objects.filter(
                    submission__employee_questionnaire_id__in=questionnaire_ids
                ).count(),

                "performance_scores": EmployeePerformanceScore.objects.filter(
                    employee_questionnaire_id__in=questionnaire_ids
                ).count(),

                "ppi_records": EmployeePastPerformanceIndex.objects.filter(
                    employee=employee,
                    review_cycle=cycle
                ).count(),

                "potential_assessments": EmployeePotentialAssessment.objects.filter(
                    employee_questionnaire_id__in=questionnaire_ids
                ).count(),

                "potential_responses": EmployeePotentialResponse.objects.filter(
                    assessment__employee_questionnaire_id__in=questionnaire_ids
                ).count(),

                "potential_scores": EmployeePotentialScore.objects.filter(
                    employee_questionnaire_id__in=questionnaire_ids
                ).count(),

                "nine_box_records": EmployeeNineBoxPlacement.objects.filter(
                    employee_questionnaire_id__in=questionnaire_ids
                ).count(),

                "appraisal_records": EmployeeAppraisalRecommendation.objects.filter(
                    employee_questionnaire_id__in=questionnaire_ids
                ).count(),

                "analytics_release_records": EmployeeAnalyticsRelease.objects.filter(
                    employee_questionnaire_id__in=questionnaire_ids
                ).count(),
            }

            response_data["delete_summary"] = summary

            if sum(summary.values()) == 0:
                response_data["warnings"].append(
                    "No PMS data found for this employee in the selected cycle."
                )
            else:
                response_data["safe_to_reset"] = True

        # =========================
        # MODE: FULL RESET
        # =========================
        else:

            questionnaire_ids = EmployeeQuestionnaire.objects.filter(
                employee=employee
            ).values_list("id", flat=True)

            summary = {
                "questionnaires": EmployeeQuestionnaire.objects.filter(
                    id__in=questionnaire_ids
                ).count(),

                "questionnaire_items": EmployeeQuestionnaireItem.objects.filter(
                    employee_questionnaire_id__in=questionnaire_ids
                ).count(),

                "stage_submissions": EmployeeQuestionnaireStageSubmission.objects.filter(
                    employee_questionnaire_id__in=questionnaire_ids
                ).count(),

                "questionnaire_responses": EmployeeQuestionnaireResponse.objects.filter(
                    submission__employee_questionnaire_id__in=questionnaire_ids
                ).count(),

                "performance_scores": EmployeePerformanceScore.objects.filter(
                    employee_questionnaire_id__in=questionnaire_ids
                ).count(),

                "ppi_records": EmployeePastPerformanceIndex.objects.filter(
                    employee=employee
                ).count(),

                "potential_assessments": EmployeePotentialAssessment.objects.filter(
                    employee_questionnaire_id__in=questionnaire_ids
                ).count(),

                "potential_responses": EmployeePotentialResponse.objects.filter(
                    assessment__employee_questionnaire_id__in=questionnaire_ids
                ).count(),

                "potential_scores": EmployeePotentialScore.objects.filter(
                    employee_questionnaire_id__in=questionnaire_ids
                ).count(),

                "nine_box_records": EmployeeNineBoxPlacement.objects.filter(
                    employee_questionnaire_id__in=questionnaire_ids
                ).count(),

                "appraisal_records": EmployeeAppraisalRecommendation.objects.filter(
                    employee_questionnaire_id__in=questionnaire_ids
                ).count(),

                "analytics_release_records": EmployeeAnalyticsRelease.objects.filter(
                    employee_questionnaire_id__in=questionnaire_ids
                ).count(),
            }

            response_data["delete_summary"] = summary

            if sum(summary.values()) == 0:
                response_data["warnings"].append(
                    "No PMS data found for this employee."
                )
            else:
                response_data["safe_to_reset"] = True

        return Response(response_data)

class EmployeeResetExecuteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if str(getattr(request.user, "employee_number", "")) != "100607":
            return Response({"error": "Not authorized"}, status=403)

        employee_number = request.data.get("employee_number")
        review_cycle_id = request.data.get("review_cycle_id")
        scope = request.data.get("scope", "cycle")
        reason = request.data.get("reason", "")

        if not employee_number:
            return Response({"error": "employee_number is required"}, status=400)

        employee = Employee.objects.filter(employee_number=employee_number).first()
        if not employee:
            return Response({"error": "Employee not found"}, status=404)

        with transaction.atomic():
            try:
                if scope == "all":
                    questionnaires = EmployeeQuestionnaire.objects.filter(employee=employee)
                    cycle = None
                else:
                    if not review_cycle_id:
                        return Response({"error": "review_cycle_id required"}, status=400)

                    cycle = ReviewCycle.objects.filter(id=review_cycle_id).first()
                    if not cycle:
                        return Response({"error": "Invalid review cycle"}, status=404)

                    questionnaires = EmployeeQuestionnaire.objects.filter(
                        employee=employee,
                        review_cycle=cycle,
                    )

                questionnaire_ids = list(questionnaires.values_list("id", flat=True))

                deleted = {
                    "questionnaires_reset": questionnaires.count(),
                    "questionnaire_items_kept": EmployeeQuestionnaireItem.objects.filter(
                        employee_questionnaire_id__in=questionnaire_ids
                    ).count(),
                    "stage_submissions": 0,
                    "questionnaire_responses": 0,
                    "performance_scores": 0,
                    "ppi_records": 0,
                    "potential_assessments": 0,
                    "potential_responses": 0,
                    "potential_scores": 0,
                    "nine_box_records": 0,
                    "appraisal_records": 0,
                    "analytics_release_records": 0,
                }

                # 1. Analytics release
                qs = EmployeeAnalyticsRelease.objects.filter(
                    employee_questionnaire_id__in=questionnaire_ids
                )
                deleted["analytics_release_records"] = qs.count()
                qs.delete()

                # 2. Appraisal
                qs = EmployeeAppraisalRecommendation.objects.filter(
                    employee_questionnaire_id__in=questionnaire_ids
                )
                deleted["appraisal_records"] = qs.count()
                qs.delete()

                # 3. Nine box
                qs = EmployeeNineBoxPlacement.objects.filter(
                    employee_questionnaire_id__in=questionnaire_ids
                )
                deleted["nine_box_records"] = qs.count()
                qs.delete()

                # 4. Potential score
                qs = EmployeePotentialScore.objects.filter(
                    employee_questionnaire_id__in=questionnaire_ids
                )
                deleted["potential_scores"] = qs.count()
                qs.delete()

                # 5. Potential responses
                qs = EmployeePotentialResponse.objects.filter(
                    assessment__employee_questionnaire_id__in=questionnaire_ids
                )
                deleted["potential_responses"] = qs.count()
                qs.delete()

                # 6. Potential assessment
                qs = EmployeePotentialAssessment.objects.filter(
                    employee_questionnaire_id__in=questionnaire_ids
                )
                deleted["potential_assessments"] = qs.count()
                qs.delete()

                # 7. Performance scores
                qs = EmployeePerformanceScore.objects.filter(
                    employee_questionnaire_id__in=questionnaire_ids
                )
                deleted["performance_scores"] = qs.count()
                qs.delete()

                # 8. PPI
                if scope == "all":
                    qs = EmployeePastPerformanceIndex.objects.filter(employee=employee)
                else:
                    qs = EmployeePastPerformanceIndex.objects.filter(
                        employee=employee,
                        review_cycle=cycle,
                    )
                deleted["ppi_records"] = qs.count()
                qs.delete()

                # 9. Questionnaire responses
                qs = EmployeeQuestionnaireResponse.objects.filter(
                    submission__employee_questionnaire_id__in=questionnaire_ids
                )
                deleted["questionnaire_responses"] = qs.count()
                qs.delete()

                # 10. Stage submissions
                qs = EmployeeQuestionnaireStageSubmission.objects.filter(
                    employee_questionnaire_id__in=questionnaire_ids
                )
                deleted["stage_submissions"] = qs.count()
                qs.delete()

                # 11. RESET questionnaire base rows instead of deleting them
                questionnaires.update(
                    status="draft",
                    submitted_at=None,
                    peer_reviewer=None,
                    peer_requested_at=None,
                )

                return Response({
                    "message": "PMS data reset successfully",
                    "employee_number": employee_number,
                    "scope": scope,
                    "review_cycle_id": review_cycle_id if scope != "all" else None,
                    "reason": reason,
                    "deleted": deleted,
                    "timestamp": timezone.now(),
                })

            except Exception as e:
                return Response(
                    {
                        "error": "Reset failed",
                        "details": str(e),
                    },
                    status=500,
                )


class AdminReviewCycleListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if str(getattr(request.user, "employee_number", "")) != "100607":
            return Response({"error": "Not authorized"}, status=403)

        cycles = ReviewCycle.objects.all().order_by("-id")

        data = [
            {
                "id": cycle.id,
                "name": cycle.name,
                "start_date": cycle.start_date,
                "end_date": cycle.end_date,
                "is_active": cycle.is_active,
            }
            for cycle in cycles
        ]

        return Response({"results": data}, status=200)