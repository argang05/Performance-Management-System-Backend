from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from evaluations.models import EmployeeQuestionnaire
from .models import (
    PotentialParameter,
    PotentialScoreConfiguration,
    EmployeePotentialAssessment,
    EmployeePotentialResponse,
    EmployeePotentialScore,
    EmployeePerformanceScore,
    EmployeePastPerformanceIndex,
)


def is_scoring_admin(user):
    return str(getattr(user, "employee_number", "")) == "100607"


def get_active_potential_config():
    return PotentialScoreConfiguration.objects.filter(is_active=True).first()


def calculate_weighted_potential_score(responses):
    total_weight = 0
    weighted_sum = 0

    for r in responses:
        weight = r.parameter.weightage
        weighted_sum += r.score * weight
        total_weight += weight

    if total_weight == 0:
        return None

    return round(weighted_sum / total_weight, 2)


class RMPotentialPendingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        questionnaires = EmployeeQuestionnaire.objects.select_related(
            "employee",
            "review_cycle",
        ).filter(
            employee__reporting_manager=request.user
        )

        results = []

        for q in questionnaires:
            has_perf_score = EmployeePerformanceScore.objects.filter(
                employee_questionnaire=q,
                final_effective_score__isnull=False
            ).exists()

            has_ppi = EmployeePastPerformanceIndex.objects.filter(
                employee=q.employee,
                review_cycle=q.review_cycle
            ).exists()

            if not (has_perf_score and has_ppi):
                continue

            assessment, _ = EmployeePotentialAssessment.objects.get_or_create(
                employee=q.employee,
                review_cycle=q.review_cycle,
                employee_questionnaire=q,
                defaults={
                    "status": "pending_rm"
                }
            )

            results.append({
                "assessment_id": assessment.id,
                "questionnaire_id": q.id,
                "employee_name": q.employee.full_name,
                "employee_number": q.employee.employee_number,
                "department": q.employee.department,
                "cycle": q.review_cycle.name if q.review_cycle else None,
                "status": assessment.status,
                "rm_submitted": assessment.rm_submitted,
                "skip_submitted": assessment.skip_submitted,
            })

        return Response({"results": results})


class SkipPotentialPendingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        questionnaires = EmployeeQuestionnaire.objects.select_related(
            "employee",
            "review_cycle",
        ).filter(
            employee__skip_level_manager=request.user
        )

        results = []

        for q in questionnaires:
            has_perf_score = EmployeePerformanceScore.objects.filter(
                employee_questionnaire=q,
                final_effective_score__isnull=False
            ).exists()

            has_ppi = EmployeePastPerformanceIndex.objects.filter(
                employee=q.employee,
                review_cycle=q.review_cycle
            ).exists()

            if not (has_perf_score and has_ppi):
                continue

            assessment, _ = EmployeePotentialAssessment.objects.get_or_create(
                employee=q.employee,
                review_cycle=q.review_cycle,
                employee_questionnaire=q,
                defaults={
                    "status": "pending_rm"
                }
            )

            results.append({
                "assessment_id": assessment.id,
                "questionnaire_id": q.id,
                "employee_name": q.employee.full_name,
                "employee_number": q.employee.employee_number,
                "department": q.employee.department,
                "cycle": q.review_cycle.name if q.review_cycle else None,
                "status": assessment.status,
                "rm_submitted": assessment.rm_submitted,
                "skip_submitted": assessment.skip_submitted,
            })

        return Response({"results": results})


class RMPotentialFormView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, assessment_id):
        assessment = get_object_or_404(
            EmployeePotentialAssessment.objects.select_related("employee"),
            id=assessment_id
        )

        if assessment.employee.reporting_manager != request.user:
            return Response({"error": "Not authorized."}, status=403)

        parameters = PotentialParameter.objects.filter(is_active=True).order_by("id")

        questions = [
            {
                "parameter_id": p.id,
                "question_text": p.question_text,
                "weightage": p.weightage,
            }
            for p in parameters
        ]

        existing = EmployeePotentialResponse.objects.filter(
            assessment=assessment,
            evaluator_type="rm"
        )

        existing_map = {r.parameter_id: r.score for r in existing}

        return Response({
            "assessment_id": assessment.id,
            "employee_name": assessment.employee.full_name,
            "department": assessment.employee.department,
            "questions": questions,
            "responses": existing_map,
        })


class SkipPotentialFormView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, assessment_id):
        assessment = get_object_or_404(
            EmployeePotentialAssessment.objects.select_related("employee"),
            id=assessment_id
        )

        if assessment.employee.skip_level_manager != request.user:
            return Response({"error": "Not authorized."}, status=403)

        parameters = PotentialParameter.objects.filter(is_active=True).order_by("id")

        questions = [
            {
                "parameter_id": p.id,
                "question_text": p.question_text,
                "weightage": p.weightage,
            }
            for p in parameters
        ]

        existing = EmployeePotentialResponse.objects.filter(
            assessment=assessment,
            evaluator_type="skip"
        )

        existing_map = {r.parameter_id: r.score for r in existing}

        return Response({
            "assessment_id": assessment.id,
            "employee_name": assessment.employee.full_name,
            "department": assessment.employee.department,
            "questions": questions,
            "responses": existing_map,
        })


class RMSavePotentialDraftView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        assessment_id = request.data.get("assessment_id")
        responses = request.data.get("responses", [])

        assessment = get_object_or_404(
            EmployeePotentialAssessment.objects.select_related("employee"),
            id=assessment_id
        )

        if assessment.employee.reporting_manager != request.user:
            return Response({"error": "Not authorized."}, status=403)

        for r in responses:
            parameter = get_object_or_404(PotentialParameter, id=r["parameter_id"])

            EmployeePotentialResponse.objects.update_or_create(
                assessment=assessment,
                parameter=parameter,
                evaluator_type="rm",
                defaults={"score": r["score"]}
            )

        return Response({"message": "RM potential draft saved."})


class SkipSavePotentialDraftView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        assessment_id = request.data.get("assessment_id")
        responses = request.data.get("responses", [])

        assessment = get_object_or_404(
            EmployeePotentialAssessment.objects.select_related("employee"),
            id=assessment_id
        )

        if assessment.employee.skip_level_manager != request.user:
            return Response({"error": "Not authorized."}, status=403)

        for r in responses:
            parameter = get_object_or_404(PotentialParameter, id=r["parameter_id"])

            EmployeePotentialResponse.objects.update_or_create(
                assessment=assessment,
                parameter=parameter,
                evaluator_type="skip",
                defaults={"score": r["score"]}
            )

        return Response({"message": "Skip potential draft saved."})


class RMSubmitPotentialView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        assessment_id = request.data.get("assessment_id")
        responses = request.data.get("responses", [])

        assessment = get_object_or_404(
            EmployeePotentialAssessment.objects.select_related("employee"),
            id=assessment_id
        )

        if assessment.employee.reporting_manager != request.user:
            return Response({"error": "Not authorized."}, status=403)

        for r in responses:
            parameter = get_object_or_404(PotentialParameter, id=r["parameter_id"])

            EmployeePotentialResponse.objects.update_or_create(
                assessment=assessment,
                parameter=parameter,
                evaluator_type="rm",
                defaults={"score": r["score"]}
            )

        assessment.rm_submitted = True

        if assessment.employee.skip_level_manager:
            assessment.status = "pending_skip"
        else:
            assessment.status = "completed"

        assessment.save()

        return Response({"message": "RM potential questionnaire submitted."})


class SkipSubmitPotentialView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        assessment_id = request.data.get("assessment_id")
        responses = request.data.get("responses", [])

        assessment = get_object_or_404(
            EmployeePotentialAssessment.objects.select_related("employee"),
            id=assessment_id
        )

        if assessment.employee.skip_level_manager != request.user:
            return Response({"error": "Not authorized."}, status=403)

        for r in responses:
            parameter = get_object_or_404(PotentialParameter, id=r["parameter_id"])

            EmployeePotentialResponse.objects.update_or_create(
                assessment=assessment,
                parameter=parameter,
                evaluator_type="skip",
                defaults={"score": r["score"]}
            )

        assessment.skip_submitted = True
        assessment.status = "completed"
        assessment.save()

        return Response({"message": "Skip potential questionnaire submitted."})


class CalculatePotentialScoreView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, assessment_id):
        if not is_scoring_admin(request.user):
            return Response({"error": "Not authorized."}, status=403)

        assessment = get_object_or_404(
            EmployeePotentialAssessment.objects.select_related("employee", "review_cycle", "employee_questionnaire"),
            id=assessment_id
        )

        if not assessment.rm_submitted:
            return Response(
                {"error": "RM potential questionnaire must be submitted first."},
                status=400
            )

        if assessment.employee.skip_level_manager and not assessment.skip_submitted:
            return Response(
                {"error": "Skip potential questionnaire must be submitted first."},
                status=400
            )

        config = get_active_potential_config()
        if not config:
            return Response(
                {"error": "No active potential score configuration found."},
                status=400
            )

        rm_responses = EmployeePotentialResponse.objects.filter(
            assessment=assessment,
            evaluator_type="rm"
        ).select_related("parameter")

        rm_score = calculate_weighted_potential_score(rm_responses)

        skip_score = None
        final_potential_score = None

        if assessment.employee.skip_level_manager:
            skip_responses = EmployeePotentialResponse.objects.filter(
                assessment=assessment,
                evaluator_type="skip"
            ).select_related("parameter")

            skip_score = calculate_weighted_potential_score(skip_responses)

            final_potential_score = round(
                (rm_score * config.rm_weight) +
                (skip_score * config.skip_weight),
                2
            )
        else:
            final_potential_score = rm_score

        score_obj, _ = EmployeePotentialScore.objects.update_or_create(
            employee=assessment.employee,
            review_cycle=assessment.review_cycle,
            employee_questionnaire=assessment.employee_questionnaire,
            defaults={
                "rm_score": rm_score,
                "skip_score": skip_score,
                "final_potential_score": final_potential_score,
            }
        )

        return Response({
            "message": "Potential score calculated successfully.",
            "assessment_id": assessment.id,
            "employee_name": assessment.employee.full_name,
            "review_cycle": assessment.review_cycle.name if assessment.review_cycle else None,
            "rm_score": score_obj.rm_score,
            "skip_score": score_obj.skip_score,
            "final_potential_score": score_obj.final_potential_score,
        })


class PotentialResultView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, assessment_id):
        if not is_scoring_admin(request.user):
            return Response({"error": "Not authorized."}, status=403)

        assessment = get_object_or_404(
            EmployeePotentialAssessment.objects.select_related("employee", "review_cycle", "employee_questionnaire"),
            id=assessment_id
        )

        score_obj = get_object_or_404(
            EmployeePotentialScore,
            employee=assessment.employee,
            review_cycle=assessment.review_cycle,
            employee_questionnaire=assessment.employee_questionnaire,
        )

        return Response({
            "assessment_id": assessment.id,
            "employee_name": assessment.employee.full_name,
            "employee_number": assessment.employee.employee_number,
            "review_cycle": assessment.review_cycle.name if assessment.review_cycle else None,
            "rm_score": score_obj.rm_score,
            "skip_score": score_obj.skip_score,
            "final_potential_score": score_obj.final_potential_score,
            "calculated_at": score_obj.calculated_at,
        })