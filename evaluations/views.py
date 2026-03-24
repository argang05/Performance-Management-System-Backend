from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Q

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
            .select_related("review_cycle", "peer_reviewer")
            .order_by("-id")
            .first()
        )

        if not questionnaire:
            return Response({"exists": False})

        return Response({
            "exists": True,
            "questionnaire_id": questionnaire.id,
            "employee_name": employee.full_name,
            "department": employee.department,
            "cycle": questionnaire.review_cycle.name if questionnaire.review_cycle else None,
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

class SkipPendingReviewsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee = request.user

        questionnaires = EmployeeQuestionnaire.objects.filter(
            employee__skip_level_manager=employee,
            status__in=["under_skip_review", "completed"]
        ).select_related("employee")

        data = []

        for q in questionnaires:
            data.append({
                "questionnaire_id": q.id,
                "employee_name": q.employee.full_name,
                "employee_number": q.employee.employee_number,
                "department": q.employee.department if q.employee.department else None,
                "status": q.status,
                "submitted_at": q.submitted_at,
            })

        return Response({"results": data})


class SkipReviewFormView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, questionnaire_id):
        questionnaire = get_object_or_404(
            EmployeeQuestionnaire,
            id=questionnaire_id
        )

        if questionnaire.employee.skip_level_manager != request.user:
            return Response(
                {"error": "Not authorized for this questionnaire"},
                status=403
            )

        items = EmployeeQuestionnaireItem.objects.filter(
            employee_questionnaire=questionnaire
        ).select_related(
            "parameter",
            "parameter__category"
        )

        questions = []

        for item in items:
            questions.append({
                "item_id": item.id,
                "question_text": item.parameter.question_text,
                "category": item.parameter.category.name if item.parameter.category else None,
                "category_type": item.parameter.category.category_type if item.parameter.category else None,
                "weightage": item.weightage,
            })

        return Response({
            "employee_name": questionnaire.employee.full_name,
            "department": questionnaire.employee.department if questionnaire.employee.department else None,
            "questions": questions
        })

class SkipSelfResponsesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, questionnaire_id):
        questionnaire = get_object_or_404(
            EmployeeQuestionnaire,
            id=questionnaire_id
        )

        if questionnaire.employee.skip_level_manager != request.user:
            return Response(
                {"error": "Not authorized for this questionnaire"},
                status=403
            )

        submission = EmployeeQuestionnaireStageSubmission.objects.filter(
            employee_questionnaire_id=questionnaire_id,
            evaluator_type="self"
        ).first()

        if not submission:
            return Response({
                "feedback": "",
                "scope_of_improvement": "",
                "responses": []
            })

        responses = EmployeeQuestionnaireResponse.objects.filter(
            submission=submission
        ).select_related(
            "questionnaire_item",
            "questionnaire_item__parameter"
        )

        data = []

        for r in responses:
            data.append({
                "question": r.questionnaire_item.parameter.question_text,
                "score": r.score,
            })

        return Response({
            "feedback": submission.feedback,
            "scope_of_improvement": submission.scope_of_improvement,
            "responses": data
        })

class SkipRMResponsesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, questionnaire_id):
        questionnaire = get_object_or_404(
            EmployeeQuestionnaire,
            id=questionnaire_id
        )

        if questionnaire.employee.skip_level_manager != request.user:
            return Response(
                {"error": "Not authorized for this questionnaire"},
                status=403
            )

        submission = EmployeeQuestionnaireStageSubmission.objects.filter(
            employee_questionnaire_id=questionnaire_id,
            evaluator_type="rm"
        ).first()

        if not submission:
            return Response({
                "feedback": "",
                "scope_of_improvement": "",
                "responses": []
            })

        responses = EmployeeQuestionnaireResponse.objects.filter(
            submission=submission
        ).select_related(
            "questionnaire_item",
            "questionnaire_item__parameter"
        )

        data = []

        for r in responses:
            data.append({
                "question": r.questionnaire_item.parameter.question_text,
                "score": r.score,
            })

        return Response({
            "feedback": submission.feedback,
            "scope_of_improvement": submission.scope_of_improvement,
            "responses": data
        })

class SkipSaveDraftView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        questionnaire_id = request.data.get("questionnaire_id")
        responses = request.data.get("responses", [])

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire,
            id=questionnaire_id
        )

        if questionnaire.employee.skip_level_manager != request.user:
            return Response(
                {"error": "Not authorized for this questionnaire"},
                status=403
            )

        submission, _ = EmployeeQuestionnaireStageSubmission.objects.get_or_create(
            employee_questionnaire=questionnaire,
            evaluator_type="skip",
            defaults={
                "submitted_by": request.user,
                "status": "draft",
            }
        )

        submission.submitted_by = request.user
        submission.status = "draft"
        submission.save()

        for r in responses:
            item = get_object_or_404(
                EmployeeQuestionnaireItem,
                id=r["item_id"],
                employee_questionnaire=questionnaire
            )

            EmployeeQuestionnaireResponse.objects.update_or_create(
                submission=submission,
                questionnaire_item=item,
                defaults={
                    "score": r["score"],
                    "reviewer_type": "skip",
                }
            )

        return Response({"message": "Skip draft saved successfully"})

class SkipSubmitReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        questionnaire_id = request.data.get("questionnaire_id")
        responses = request.data.get("responses", [])
        feedback = request.data.get("feedback")
        scope = request.data.get("scope_of_improvement")

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire,
            id=questionnaire_id
        )

        if questionnaire.employee.skip_level_manager != request.user:
            return Response(
                {"error": "Not authorized for this questionnaire"},
                status=403
            )

        submission, _ = EmployeeQuestionnaireStageSubmission.objects.get_or_create(
            employee_questionnaire=questionnaire,
            evaluator_type="skip",
            defaults={
                "submitted_by": request.user,
                "status": "draft",
            }
        )

        submission.submitted_by = request.user
        submission.feedback = feedback
        submission.scope_of_improvement = scope
        submission.status = "submitted"
        submission.submitted_at = timezone.now()
        submission.save()

        for r in responses:
            item = get_object_or_404(
                EmployeeQuestionnaireItem,
                id=r["item_id"],
                employee_questionnaire=questionnaire
            )

            EmployeeQuestionnaireResponse.objects.update_or_create(
                submission=submission,
                questionnaire_item=item,
                defaults={
                    "score": r["score"],
                    "reviewer_type": "skip",
                }
            )

        if questionnaire.peer_reviewer:
            questionnaire.status = "under_peer_review"
        else:
            questionnaire.status = "completed"

        questionnaire.save()

        return Response({"message": "Skip review submitted successfully"})

class PeerEmployeeSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        User = get_user_model()

        query = request.query_params.get("q", "").strip()
        employee = request.user

        excluded_ids = [
            employee.id,
            employee.reporting_manager_id,
            employee.skip_level_manager_id,
        ]
        excluded_ids = [x for x in excluded_ids if x]

        employees = User.objects.filter(
            band=employee.band,
            is_active=True
        ).exclude(
            id__in=excluded_ids
        )

        if query:
            employees = employees.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(employee_number__icontains=query)
            )

        employees = employees.order_by("first_name", "last_name")[:25]

        data = []
        for e in employees:
            data.append({
                "id": e.id,
                "employee_number": e.employee_number,
                "full_name": e.full_name,
                "department": e.department,
            })

        return Response(data)

class PeerRecommendView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        User = get_user_model()

        questionnaire_id = request.data.get("questionnaire_id")
        peer_id = request.data.get("peer_employee_id")

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire,
            id=questionnaire_id
        )

        if questionnaire.employee != request.user:
            return Response(
                {"error": "You cannot recommend peer for this questionnaire."},
                status=403
            )

        peer = get_object_or_404(User, id=peer_id)

        employee = request.user

        if peer.band != employee.band:
            return Response(
                {"error": "Peer reviewer must belong to same band."},
                status=400
            )

        if peer.id == employee.id:
            return Response(
                {"error": "You cannot recommend yourself as peer reviewer."},
                status=400
            )

        if employee.reporting_manager_id and peer.id == employee.reporting_manager_id:
            return Response(
                {"error": "Reporting manager cannot be peer reviewer."},
                status=400
            )

        if employee.skip_level_manager_id and peer.id == employee.skip_level_manager_id:
            return Response(
                {"error": "Skip level manager cannot be peer reviewer."},
                status=400
            )

        questionnaire.peer_reviewer = peer
        questionnaire.peer_requested_at = timezone.now()
        questionnaire.status = "under_peer_review"
        questionnaire.save()

        return Response({"message": "Peer review request sent successfully"})


class PeerPendingReviewsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        peer = request.user

        questionnaires = EmployeeQuestionnaire.objects.filter(
            peer_reviewer=peer,
            status__in=["under_peer_review", "completed"]
        ).select_related("employee")

        data = []

        for q in questionnaires:

            peer_submission = EmployeeQuestionnaireStageSubmission.objects.filter(
                employee_questionnaire=q,
                evaluator_type="peer",
                status="submitted"
            ).exists()

            data.append({
                "questionnaire_id": q.id,
                "employee_name": q.employee.full_name,
                "employee_number": q.employee.employee_number,
                "department": q.employee.department,
                "cycle": q.review_cycle.name if q.review_cycle else None,
                "submitted_at": q.submitted_at,
                "peer_completed": peer_submission
            })

        return Response({"results": data})

class PeerReviewFormView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, questionnaire_id):

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire,
            id=questionnaire_id
        )

        if questionnaire.peer_reviewer != request.user:
            return Response(
                {"error": "Not authorized for this questionnaire"},
                status=403
            )

        items = EmployeeQuestionnaireItem.objects.filter(
            employee_questionnaire=questionnaire
        ).select_related(
            "parameter",
            "parameter__category"
        )

        questions = []

        for item in items:
            questions.append({
                "item_id": item.id,
                "question_text": item.parameter.question_text,
                "category": item.parameter.category.name if item.parameter.category else None,
                "category_type": item.parameter.category.category_type if item.parameter.category else None
            })

        return Response({
            "employee_name": questionnaire.employee.full_name,
            "department": questionnaire.employee.department,
            "questions": questions
        })

class PeerSaveDraftView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        questionnaire_id = request.data.get("questionnaire_id")
        responses = request.data.get("responses", [])

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire,
            id=questionnaire_id
        )

        if questionnaire.peer_reviewer != request.user:
            return Response(
                {"error": "Not authorized"},
                status=403
            )

        submission, _ = EmployeeQuestionnaireStageSubmission.objects.get_or_create(
            employee_questionnaire=questionnaire,
            evaluator_type="peer",
            defaults={
                "submitted_by": request.user,
                "status": "draft"
            }
        )

        for r in responses:

            item = get_object_or_404(
                EmployeeQuestionnaireItem,
                id=r["item_id"],
                employee_questionnaire=questionnaire
            )

            EmployeeQuestionnaireResponse.objects.update_or_create(
                submission=submission,
                questionnaire_item=item,
                defaults={
                    "score": r["score"],
                    "reviewer_type": "peer"
                }
            )

        return Response({"message": "Draft saved"})

class PeerSubmitReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        questionnaire_id = request.data.get("questionnaire_id")
        responses = request.data.get("responses", [])
        feedback = request.data.get("feedback")
        scope = request.data.get("scope_of_improvement")

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire,
            id=questionnaire_id
        )

        if questionnaire.peer_reviewer != request.user:
            return Response(
                {"error": "Not authorized"},
                status=403
            )

        submission, _ = EmployeeQuestionnaireStageSubmission.objects.get_or_create(
            employee_questionnaire=questionnaire,
            evaluator_type="peer"
        )

        submission.submitted_by = request.user
        submission.feedback = feedback
        submission.scope_of_improvement = scope
        submission.status = "submitted"
        submission.submitted_at = timezone.now()
        submission.save()

        for r in responses:

            item = get_object_or_404(
                EmployeeQuestionnaireItem,
                id=r["item_id"],
                employee_questionnaire=questionnaire
            )

            EmployeeQuestionnaireResponse.objects.update_or_create(
                submission=submission,
                questionnaire_item=item,
                defaults={
                    "score": r["score"],
                    "reviewer_type": "peer"
                }
            )

        questionnaire.status = "completed"
        questionnaire.save()

        return Response({"message": "Peer review submitted successfully"})

class PeerSelfResponsesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, questionnaire_id):

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire,
            id=questionnaire_id
        )

        if questionnaire.peer_reviewer != request.user:
            return Response({"error": "Not authorized"}, status=403)

        submission = EmployeeQuestionnaireStageSubmission.objects.filter(
            employee_questionnaire=questionnaire,
            evaluator_type="self"
        ).first()

        responses = EmployeeQuestionnaireResponse.objects.filter(
            submission=submission
        ).select_related(
            "questionnaire_item",
            "questionnaire_item__parameter"
        )

        data = []

        for r in responses:
            data.append({
                "question": r.questionnaire_item.parameter.question_text,
                "score": r.score
            })

        return Response({
            "feedback": submission.feedback,
            "scope_of_improvement": submission.scope_of_improvement,
            "responses": data
        })