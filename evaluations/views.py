from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
from django.http import Http404

from .models import *
from .serializers import *


class SelfQuestionnaireView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee = request.user

        cycle = ReviewCycle.objects.filter(is_active=True).first()
        if not cycle:
            return Response(
                {"detail": "No active review cycle found."},
                status=404,
            )

        questionnaire, _ = EmployeeQuestionnaire.objects.get_or_create(
            employee=employee,
            review_cycle=cycle,
            defaults={"status": "draft"},
        )

        # If questionnaire items are missing, regenerate them
        if not questionnaire.items.exists():
            self._generate_questionnaire_items(questionnaire, employee)

        items = questionnaire.items.select_related(
            "parameter",
            "parameter__category",
        ).all()

        data = [
            {
                "id": item.id,
                "question_text": item.parameter.question_text,
                "category": item.parameter.category.name,
                "category_type": item.parameter.category.category_type,
                "weightage": item.weightage,
                "order": item.order,
            }
            for item in items
        ]

        return Response(
            {
                "questionnaire_id": questionnaire.id,
                "questions": data,
            },
            status=200,
        )

    def _generate_questionnaire_items(self, questionnaire, employee):
        """
        Rebuild questionnaire items for this employee if they are missing.
        Creates:
        - common behavioural questions (department is NULL)
        - department-specific performance questions
        """
        department = employee.department

        behavioral_questions = QuestionParameter.objects.filter(
            category__category_type="behavioral",
            department__isnull=True,
            is_active=True,
        ).order_by("id")[:5]

        performance_questions = QuestionParameter.objects.filter(
            category__category_type="performance",
            department=department,
            is_active=True,
        ).order_by("id")[:5]

        order_counter = 1

        for question in behavioral_questions:
            EmployeeQuestionnaireItem.objects.get_or_create(
                employee_questionnaire=questionnaire,
                parameter=question,
                defaults={
                    "weightage": question.default_weightage,
                    "order": order_counter,
                },
            )
            order_counter += 1

        for question in performance_questions:
            EmployeeQuestionnaireItem.objects.get_or_create(
                employee_questionnaire=questionnaire,
                parameter=question,
                defaults={
                    "weightage": question.default_weightage,
                    "order": order_counter,
                },
            )
            order_counter += 1

class SaveSelfEvaluation(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        questionnaire_id = request.data.get("questionnaire_id")

        feedback = request.data.get("feedback")
        improvement = request.data.get("scope_of_improvement")

        responses = request.data.get("responses")

        questionnaire = EmployeeQuestionnaire.objects.get(id=questionnaire_id)

        submission, _ = EmployeeQuestionnaireStageSubmission.objects.get_or_create(
            employee_questionnaire=questionnaire,
            evaluator_type="self"
        )

        submission.feedback = feedback
        submission.scope_of_improvement = improvement
        submission.status = "draft"
        submission.submitted_by = request.user
        submission.save()

        for r in responses:

            item = EmployeeQuestionnaireItem.objects.get(id=r["item_id"])

            EmployeeQuestionnaireResponse.objects.update_or_create(
                submission=submission,
                questionnaire_item=item,
                defaults={
                    "score": r["score"]
                }
            )

        return Response({"message": "Draft saved"})

class SubmitSelfEvaluation(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        questionnaire_id = request.data.get("questionnaire_id")

        questionnaire = EmployeeQuestionnaire.objects.get(id=questionnaire_id)

        submission = EmployeeQuestionnaireStageSubmission.objects.get(
            employee_questionnaire=questionnaire,
            evaluator_type="self"
        )

        submission.status = "submitted"
        submission.submitted_at = timezone.now()
        submission.save()

        questionnaire.status = "self_submitted"
        questionnaire.submitted_at = timezone.now()
        questionnaire.save()

        return Response({"message": "Self evaluation submitted"})

class DeleteEmployeeQuestionnaireView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def delete(self, request, questionnaire_id):
        try:
            questionnaire = EmployeeQuestionnaire.objects.get(id=questionnaire_id)
        except EmployeeQuestionnaire.DoesNotExist:
            return Response(
                {"error": "Questionnaire not found."},
                status=404,
            )

        # First delete responses linked through stage submissions
        submissions = EmployeeQuestionnaireStageSubmission.objects.filter(
            employee_questionnaire=questionnaire
        )

        EmployeeQuestionnaireResponse.objects.filter(
            submission__in=submissions
        ).delete()

        # Then delete stage submissions
        submissions.delete()

        # Then delete questionnaire items
        EmployeeQuestionnaireItem.objects.filter(
            employee_questionnaire=questionnaire
        ).delete()

        # Finally delete questionnaire
        questionnaire.delete()

        return Response(
            {"message": "Questionnaire deleted successfully."},
            status=200,
        )

class SelfReviewStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        employee = request.user

        questionnaire = (
            EmployeeQuestionnaire.objects
            .filter(employee=employee)
            .select_related("review_cycle")
            .order_by("-id")
            .first()
        )

        if not questionnaire:
            return Response({"exists": False})

        return Response({
            "exists": True,
            "employee_name": employee.full_name,
            "department": employee.department,
            "cycle": questionnaire.review_cycle.name,
            "status": questionnaire.status,
            "submitted_at": questionnaire.submitted_at,
            "peer_reviewer": (
                questionnaire.peer_reviewer.full_name
                if questionnaire.peer_reviewer else None
            )
        })

class RecommendPeerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        questionnaire_id = request.data.get("questionnaire_id")
        peer_id = request.data.get("peer_id")

        questionnaire = EmployeeQuestionnaire.objects.get(
            id=questionnaire_id,
            employee=request.user
        )

        peer = Employee.objects.get(id=peer_id)

        questionnaire.peer_reviewer = peer
        questionnaire.peer_requested_at = timezone.now()
        questionnaire.save()

        return Response({"message": "Peer recommended successfully"})

class ReportingManagerQueueView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        manager = request.user

        questionnaires = (
            EmployeeQuestionnaire.objects
            .filter(employee__reporting_manager=manager)
            .select_related("employee", "review_cycle")
            .order_by("-id")
        )

        data = []

        for q in questionnaires:
            data.append({
                "questionnaire_id": q.id,
                "employee_name": q.employee.full_name,
                "employee_number": q.employee.employee_number,
                "department": q.employee.department,
                "submitted_at": q.submitted_at,
                "cycle": q.review_cycle.name,
                "status": q.status,
            })

        return Response(data)

class RMReviewFormView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, questionnaire_id):
        questionnaire = EmployeeQuestionnaire.objects.select_related(
            "employee"
        ).get(id=questionnaire_id)

        if questionnaire.employee.reporting_manager_id != request.user.id:
            return Response(
                {"error": "Not authorized to review this questionnaire"},
                status=403
            )

        items = (
            EmployeeQuestionnaireItem.objects
            .filter(employee_questionnaire=questionnaire)
            .select_related("parameter", "parameter__category")
            .order_by("order")
        )

        questions = []

        for item in items:
            questions.append({
                "item_id": item.id,
                "question_text": item.parameter.question_text,
                "category": item.parameter.category.name,
                "category_type": item.parameter.category.category_type,
                "weightage": item.weightage,
                "order": item.order,
            })

        return Response({
            "questionnaire_id": questionnaire.id,
            "employee_name": questionnaire.employee.full_name,
            "department": questionnaire.employee.department,
            "questions": questions,
        })

class RMViewSelfResponses(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, questionnaire_id):
        questionnaire = EmployeeQuestionnaire.objects.select_related(
            "employee"
        ).get(id=questionnaire_id)

        if questionnaire.employee.reporting_manager_id != request.user.id:
            return Response(
                {"error": "Not authorized"},
                status=403
            )

        responses = (
            EmployeeQuestionnaireResponse.objects
            .filter(
                submission__employee_questionnaire=questionnaire,
                reviewer_type="self"
            )
            .select_related("questionnaire_item__parameter")
            .order_by("questionnaire_item__order")
        )

        data = []

        for r in responses:
            data.append({
                "question": r.questionnaire_item.parameter.question_text,
                "score": r.score
            })

        submission = EmployeeQuestionnaireStageSubmission.objects.filter(
            employee_questionnaire=questionnaire,
            evaluator_type="self"
        ).first()

        return Response({
            "responses": data,
            "feedback": submission.feedback if submission else "",
            "scope_of_improvement": submission.scope_of_improvement if submission else ""
        })

class RMSaveDraftView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        questionnaire_id = request.data.get("questionnaire_id")
        responses = request.data.get("responses")

        questionnaire = EmployeeQuestionnaire.objects.get(id=questionnaire_id)

        submission, _ = EmployeeQuestionnaireStageSubmission.objects.get_or_create(
            employee_questionnaire=questionnaire,
            evaluator_type="rm"
        )

        for r in responses:

            item = EmployeeQuestionnaireItem.objects.get(id=r["item_id"])

            EmployeeQuestionnaireResponse.objects.update_or_create(
                submission=submission,
                questionnaire_item=item,
                reviewer_type="rm",
                defaults={"score": r["score"]}
            )

        return Response({"message": "Draft saved"})



class RMSubmitReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        questionnaire_id = request.data.get("questionnaire_id")
        responses = request.data.get("responses")
        feedback = request.data.get("feedback")
        scope = request.data.get("scope_of_improvement")

        questionnaire = EmployeeQuestionnaire.objects.select_related(
            "employee"
        ).get(id=questionnaire_id)

        submission, _ = EmployeeQuestionnaireStageSubmission.objects.get_or_create(
            employee_questionnaire=questionnaire,
            evaluator_type="rm"
        )

        submission.feedback = feedback
        submission.scope_of_improvement = scope
        submission.submitted_at = timezone.now()
        submission.save()

        for r in responses:

            item = EmployeeQuestionnaireItem.objects.get(id=r["item_id"])

            EmployeeQuestionnaireResponse.objects.update_or_create(
                submission=submission,
                questionnaire_item=item,
                reviewer_type="rm",
                defaults={"score": r["score"]}
            )

        rm_band = request.user.band

        questionnaire.status = "rm_reviewed"

        if rm_band in ["SM1", "SM2"]:
            questionnaire.status = "completed"
        else:
            questionnaire.status = "under_skip_review"

        questionnaire.save()

        return Response({"message": "RM Review Submitted"})