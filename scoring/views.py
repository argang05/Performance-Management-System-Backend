from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Exists, OuterRef
from django.contrib.auth import get_user_model

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from evaluations.models import (
    EmployeeQuestionnaire,
    EmployeeQuestionnaireStageSubmission,
    EmployeeQuestionnaireResponse,
)

from .models import EmployeePerformanceScore
from .serializers import (
    EmployeePerformanceScoreSerializer,
    HRScoreOverrideSerializer,
    ReleaseScoreSerializer,
)
from .services import (
    get_active_config,
    weighted_category_score,
    calculate_evaluator_score,
    normalize_weights,
    calculate_final_score,
)

from .models import EmployeePastPerformanceIndex
from .models import EmployeePerformanceScore, EmployeePotentialAssessment
from .services_ppi import get_past_scores, save_ppi

User = get_user_model()


def is_scoring_admin(user):
    return str(getattr(user, "employee_number", "")) == "100607"


class AdminScoringQuestionnaireListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if str(getattr(request.user, "employee_number", "")) != "100607":
            return Response({"error": "Not authorized."}, status=403)

        score_subquery = EmployeePerformanceScore.objects.filter(
            employee_questionnaire=OuterRef("pk")
        )

        assessment_subquery = EmployeePotentialAssessment.objects.filter(
            employee_questionnaire=OuterRef("pk")
        )

        questionnaires = (
            EmployeeQuestionnaire.objects.select_related("employee", "review_cycle")
            .annotate(
                has_score=Exists(score_subquery),
                has_potential_assessment=Exists(assessment_subquery),
            )
            .order_by("-id")
        )

        assessment_map = {
            item.employee_questionnaire_id: item.id
            for item in EmployeePotentialAssessment.objects.filter(
                employee_questionnaire_id__in=[q.id for q in questionnaires]
            )
        }

        results = []
        for q in questionnaires:
            results.append({
                "questionnaire_id": q.id,
                "assessment_id": assessment_map.get(q.id),
                "employee_name": q.employee.full_name,
                "employee_number": q.employee.employee_number,
                "department": q.employee.department,
                "cycle": q.review_cycle.name if q.review_cycle else None,
                "status": q.status,
                "has_score": q.has_score,
            })

        return Response({"results": results})

class CalculateScoreView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, questionnaire_id):
        if not is_scoring_admin(request.user):
            return Response(
                {"error": "You are not authorized to calculate scores."},
                status=403
            )

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire,
            id=questionnaire_id
        )

        config = get_active_config()

        if not config:
            return Response(
                {"error": "No active scoring configuration found."},
                status=400
            )

        submissions = EmployeeQuestionnaireStageSubmission.objects.filter(
            employee_questionnaire=questionnaire,
            status="submitted"
        )

        evaluator_scores = {}
        category_scores = {}
        active_evaluators = []

        for submission in submissions:
            evaluator = submission.evaluator_type

            if evaluator not in ["self", "rm", "skip", "peer"]:
                continue

            responses = EmployeeQuestionnaireResponse.objects.filter(
                submission=submission
            ).select_related(
                "questionnaire_item",
                "questionnaire_item__parameter__category"
            )

            behavioural_responses = []
            performance_responses = []

            for r in responses:
                category = getattr(r.questionnaire_item.parameter, "category", None)
                category_type = str(getattr(category, "category_type", "")).strip().lower()

                if category_type in ["behavioral", "behavioural"]:
                    behavioural_responses.append(r)

                if category_type == "performance":
                    performance_responses.append(r)

            behavioural_score = weighted_category_score(behavioural_responses)
            performance_score = weighted_category_score(performance_responses)

            category_scores[f"{evaluator}_behavioural"] = behavioural_score
            category_scores[f"{evaluator}_performance"] = performance_score

            evaluator_score = calculate_evaluator_score(
                behavioural_score,
                performance_score,
                config
            )

            evaluator_scores[evaluator] = evaluator_score

            if evaluator_score is not None:
                active_evaluators.append(evaluator)

        if not active_evaluators:
            return Response(
                {"error": "No valid submitted evaluator scores found for calculation."},
                status=400
            )

        normalized_weights = normalize_weights(active_evaluators, config)
        final_score = calculate_final_score(evaluator_scores, normalized_weights)

        score_obj, _ = EmployeePerformanceScore.objects.get_or_create(
            employee_questionnaire=questionnaire,
            defaults={
                "employee": questionnaire.employee,
                "review_cycle": questionnaire.review_cycle
            }
        )

        score_obj.self_behavioural_score = category_scores.get("self_behavioural")
        score_obj.self_performance_score = category_scores.get("self_performance")

        score_obj.rm_behavioural_score = category_scores.get("rm_behavioural")
        score_obj.rm_performance_score = category_scores.get("rm_performance")

        score_obj.skip_behavioural_score = category_scores.get("skip_behavioural")
        score_obj.skip_performance_score = category_scores.get("skip_performance")

        score_obj.peer_behavioural_score = category_scores.get("peer_behavioural")
        score_obj.peer_performance_score = category_scores.get("peer_performance")

        score_obj.self_score = evaluator_scores.get("self")
        score_obj.rm_score = evaluator_scores.get("rm")
        score_obj.skip_score = evaluator_scores.get("skip")
        score_obj.peer_score = evaluator_scores.get("peer")

        score_obj.effective_self_weight = normalized_weights.get("self")
        score_obj.effective_rm_weight = normalized_weights.get("rm")
        score_obj.effective_skip_weight = normalized_weights.get("skip")
        score_obj.effective_peer_weight = normalized_weights.get("peer")

        score_obj.system_final_score = final_score

        if score_obj.hr_override_score is not None:
            score_obj.final_effective_score = score_obj.hr_override_score
        else:
            score_obj.final_effective_score = final_score

        score_obj.save()

        serializer = EmployeePerformanceScoreSerializer(score_obj)
        return Response(serializer.data)


class ScoreResultView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, questionnaire_id):
        if not is_scoring_admin(request.user):
            return Response(
                {"error": "You are not authorized to view full score results."},
                status=403
            )

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire,
            id=questionnaire_id
        )

        score = get_object_or_404(
            EmployeePerformanceScore,
            employee_questionnaire=questionnaire
        )

        serializer = EmployeePerformanceScoreSerializer(score)
        return Response(serializer.data)


class HRScoreOverrideView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, questionnaire_id):
        if not is_scoring_admin(request.user):
            return Response(
                {"error": "You are not authorized to override scores."},
                status=403
            )

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire,
            id=questionnaire_id
        )

        score = get_object_or_404(
            EmployeePerformanceScore,
            employee_questionnaire=questionnaire
        )

        serializer = HRScoreOverrideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        score.hr_override_score = round(serializer.validated_data["hr_override_score"], 2)
        score.override_reason = serializer.validated_data["override_reason"]
        score.overridden_by = request.user
        score.overridden_at = timezone.now()
        score.final_effective_score = score.hr_override_score
        score.save()

        return Response({
            "message": "Score override applied successfully.",
            "final_effective_score": score.final_effective_score,
            "hr_override_score": score.hr_override_score,
            "override_reason": score.override_reason,
        })


class ReleaseScoreView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, questionnaire_id):
        if not is_scoring_admin(request.user):
            return Response(
                {"error": "You are not authorized to release scores."},
                status=403
            )

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire,
            id=questionnaire_id
        )

        score = get_object_or_404(
            EmployeePerformanceScore,
            employee_questionnaire=questionnaire
        )

        serializer = ReleaseScoreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        is_released = serializer.validated_data["is_released_to_employee"]

        score.is_released_to_employee = is_released

        if is_released:
            score.released_by = request.user
            score.released_at = timezone.now()
        else:
            score.released_by = None
            score.released_at = None

        score.save()

        return Response({
            "message": "Score release status updated successfully.",
            "is_released_to_employee": score.is_released_to_employee,
            "released_at": score.released_at,
        })


class MyScoreView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, questionnaire_id):
        questionnaire = get_object_or_404(
            EmployeeQuestionnaire,
            id=questionnaire_id,
            employee=request.user
        )

        score = get_object_or_404(
            EmployeePerformanceScore,
            employee_questionnaire=questionnaire
        )

        if not score.is_released_to_employee:
            return Response(
                {"message": "Your score has not been released yet."},
                status=403
            )

        return Response({
            "questionnaire_id": questionnaire.id,
            "employee_name": questionnaire.employee.full_name,
            "review_cycle": questionnaire.review_cycle.name if questionnaire.review_cycle else None,
            "final_effective_score": score.final_effective_score,
            "system_final_score": score.system_final_score,
            "is_released_to_employee": score.is_released_to_employee,
            "potential_score": score.potential_score,
            "nine_box_label": score.nine_box_label,
        })

class CalculatePPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, questionnaire_id):
        if not is_scoring_admin(request.user):
            return Response(
                {"error": "You are not authorized to calculate PPI."},
                status=403
            )

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire,
            id=questionnaire_id
        )

        score_obj = get_object_or_404(
            EmployeePerformanceScore,
            employee_questionnaire=questionnaire
        )

        current_score = score_obj.final_effective_score

        if current_score is None:
            return Response(
                {"error": "Final effective score is not available for this questionnaire."},
                status=400
            )

        past_scores = get_past_scores(
            employee=questionnaire.employee,
            current_cycle=questionnaire.review_cycle
        )

        ppi_obj = save_ppi(
            employee=questionnaire.employee,
            cycle=questionnaire.review_cycle,
            current_score=current_score,
            past_scores=past_scores
        )

        return Response({
            "message": "PPI calculated successfully.",
            "employee_name": questionnaire.employee.full_name,
            "review_cycle": questionnaire.review_cycle.name if questionnaire.review_cycle else None,
            "current_cycle_score": ppi_obj.current_cycle_score,
            "previous_cycle_score_1": ppi_obj.previous_cycle_score_1,
            "previous_cycle_score_2": ppi_obj.previous_cycle_score_2,
            "ppi_score": ppi_obj.ppi_score,
        })


class PPIResultView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, questionnaire_id):
        if not is_scoring_admin(request.user):
            return Response(
                {"error": "You are not authorized to view PPI results."},
                status=403
            )

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire,
            id=questionnaire_id
        )

        ppi_obj = get_object_or_404(
            EmployeePastPerformanceIndex,
            employee=questionnaire.employee,
            review_cycle=questionnaire.review_cycle
        )

        return Response({
            "employee_name": questionnaire.employee.full_name,
            "employee_number": questionnaire.employee.employee_number,
            "review_cycle": questionnaire.review_cycle.name if questionnaire.review_cycle else None,
            "current_cycle_score": ppi_obj.current_cycle_score,
            "previous_cycle_score_1": ppi_obj.previous_cycle_score_1,
            "previous_cycle_score_2": ppi_obj.previous_cycle_score_2,
            "ppi_score": ppi_obj.ppi_score,
            "calculated_at": ppi_obj.calculated_at,
        })