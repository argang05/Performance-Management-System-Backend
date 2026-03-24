from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.shortcuts import get_object_or_404

from evaluations.models import (
    EmployeeQuestionnaire,
    EmployeeQuestionnaireStageSubmission,
    EmployeeQuestionnaireResponse
)

from .models import EmployeePerformanceScore
from .serializers import EmployeePerformanceScoreSerializer
from .services import (
    get_active_config,
    weighted_category_score,
    calculate_evaluator_score,
    normalize_weights,
    calculate_final_score
)
from django.contrib.auth import get_user_model
from django.db.models import Exists, OuterRef

User = get_user_model()


class CalculateScoreView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, questionnaire_id):

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire,
            id=questionnaire_id
        )

        config = get_active_config()

        submissions = EmployeeQuestionnaireStageSubmission.objects.filter(
            employee_questionnaire=questionnaire,
            status="submitted"
        )

        evaluator_scores = {}
        category_scores = {}

        active_evaluators = []

        for submission in submissions:

            evaluator = submission.evaluator_type

            responses = EmployeeQuestionnaireResponse.objects.filter(
                submission=submission
            ).select_related(
                "questionnaire_item",
                "questionnaire_item__parameter__category"
            )

            behavioural_responses = []
            performance_responses = []

            for r in responses:

                category_type = r.questionnaire_item.parameter.category.category_type

                if category_type == "behavioral":
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

            active_evaluators.append(evaluator)

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
        score_obj.final_effective_score = final_score

        score_obj.save()

        serializer = EmployeePerformanceScoreSerializer(score_obj)

        return Response(serializer.data)

class ScoreResultView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, questionnaire_id):

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

class AdminScoringQuestionnaireListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Temporary admin rule for testing
        if str(request.user.employee_number) != "100607":
            return Response(
                {"error": "You are not authorized to access scoring console."},
                status=403
            )

        score_subquery = EmployeePerformanceScore.objects.filter(
            employee_questionnaire=OuterRef("pk")
        )

        questionnaires = (
            EmployeeQuestionnaire.objects
            .select_related("employee", "review_cycle", "peer_reviewer")
            .annotate(has_score=Exists(score_subquery))
            .order_by("-id")
        )

        results = []

        for q in questionnaires:
            results.append({
                "questionnaire_id": q.id,
                "employee_name": q.employee.full_name,
                "employee_number": q.employee.employee_number,
                "department": q.employee.department,
                "cycle": q.review_cycle.name if q.review_cycle else None,
                "status": q.status,
                "peer_reviewer": q.peer_reviewer.full_name if q.peer_reviewer else None,
                "has_score": q.has_score,
            })

        return Response({"results": results})