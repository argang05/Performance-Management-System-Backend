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

    @transaction.atomic
    def get(self, request):
        employee = request.user

        cycle = ReviewCycle.objects.filter(is_active=True).first()
        if not cycle:
            return Response(
                {"detail": "No active review cycle found."},
                status=404,
            )

        questionnaire = (
            EmployeeQuestionnaire.objects
            .select_for_update()
            .filter(employee=employee, review_cycle=cycle)
            .order_by("id")
            .first()
        )

        if not questionnaire:
            questionnaire = EmployeeQuestionnaire.objects.create(
                employee=employee,
                review_cycle=cycle,
                status="draft",
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

    @transaction.atomic
    def post(self, request):
        questionnaire_id = request.data.get("questionnaire_id")
        feedback = request.data.get("feedback")
        scope_of_improvement = request.data.get("scope_of_improvement")
        responses = request.data.get("responses", [])

        if not questionnaire_id:
            return Response(
                {"error": "questionnaire_id is required."},
                status=400
            )

        if not isinstance(responses, list) or not responses:
            return Response(
                {"error": "Responses cannot be empty."},
                status=400
            )

        if not feedback or not str(feedback).strip():
            return Response(
                {"error": "Feedback is required."},
                status=400
            )

        if not scope_of_improvement or not str(scope_of_improvement).strip():
            return Response(
                {"error": "Scope of improvement is required."},
                status=400
            )

        questionnaire = EmployeeQuestionnaire.objects.filter(
            id=questionnaire_id,
            employee=request.user,
        ).first()

        if not questionnaire:
            return Response(
                {"error": "Questionnaire not found or not authorized."},
                status=404
            )

        submission, _ = EmployeeQuestionnaireStageSubmission.objects.get_or_create(
            employee_questionnaire=questionnaire,
            evaluator_type="self",
            defaults={
                "submitted_by": request.user,
                "status": "draft",
            }
        )

        now = timezone.now()

        try:
            item_ids = [int(r["item_id"]) for r in responses]
        except (KeyError, TypeError, ValueError):
            return Response(
                {"error": "Each response must contain a valid item_id."},
                status=400
            )

        items = EmployeeQuestionnaireItem.objects.filter(
            id__in=item_ids,
            employee_questionnaire=questionnaire
        )

        item_map = {item.id: item for item in items}

        missing_item_ids = [item_id for item_id in item_ids if item_id not in item_map]
        if missing_item_ids:
            return Response(
                {"error": f"Invalid questionnaire item ids: {missing_item_ids}"},
                status=400
            )

        existing_responses = EmployeeQuestionnaireResponse.objects.filter(
            submission=submission,
            questionnaire_item_id__in=item_ids,
            reviewer_type="self",
        )

        existing_map = {
            response.questionnaire_item_id: response
            for response in existing_responses
        }

        responses_to_update = []
        responses_to_create = []

        for r in responses:
            try:
                item_id = int(r["item_id"])
                score = int(r["score"])
            except (KeyError, TypeError, ValueError):
                return Response(
                    {"error": "Each response must contain valid item_id and score."},
                    status=400
                )

            item = item_map[item_id]
            existing = existing_map.get(item_id)

            if existing:
                existing.score = score
                existing.reviewer_type = "self"
                responses_to_update.append(existing)
            else:
                responses_to_create.append(
                    EmployeeQuestionnaireResponse(
                        submission=submission,
                        questionnaire_item=item,
                        reviewer_type="self",
                        score=score,
                    )
                )

        if responses_to_update:
            EmployeeQuestionnaireResponse.objects.bulk_update(
                responses_to_update,
                ["score", "reviewer_type"]
            )

        if responses_to_create:
            EmployeeQuestionnaireResponse.objects.bulk_create(responses_to_create)

        submission.feedback = feedback
        submission.scope_of_improvement = scope_of_improvement
        submission.status = "submitted"
        submission.submitted_at = now
        submission.submitted_by = request.user
        submission.save(
            update_fields=[
                "feedback",
                "scope_of_improvement",
                "status",
                "submitted_at",
                "submitted_by",
            ]
        )

        questionnaire.status = "under_rm_review"
        questionnaire.submitted_at = now
        questionnaire.save(update_fields=["status", "submitted_at"])

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

        peer_completed = EmployeeQuestionnaireStageSubmission.objects.filter(
            employee_questionnaire=questionnaire,
            evaluator_type="peer",
            status="submitted"
        ).exists()

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
            ),
            "peer_completed": peer_completed,
        })

class RecommendPeerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        questionnaire_id = request.data.get("questionnaire_id")
        peer_id = request.data.get("peer_id")

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire,
            id=questionnaire_id,
            employee=request.user
        )

        peer = get_object_or_404(Employee, id=peer_id)

        if peer.id == request.user.id:
            return Response(
                {"error": "You cannot recommend yourself as peer reviewer."},
                status=400
            )

        questionnaire.peer_reviewer = peer
        questionnaire.peer_requested_at = timezone.now()
        questionnaire.save(update_fields=["peer_reviewer", "peer_requested_at"])

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
        responses = request.data.get("responses", [])

        questionnaire = EmployeeQuestionnaire.objects.get(id=questionnaire_id)

        submission, _ = EmployeeQuestionnaireStageSubmission.objects.get_or_create(
            employee_questionnaire=questionnaire,
            evaluator_type="rm"
        )

        submission.submitted_by = request.user
        submission.status = "draft"
        submission.save()

        for r in responses:

            item = EmployeeQuestionnaireItem.objects.get(
                id=r["item_id"],
                employee_questionnaire=questionnaire
            )

            EmployeeQuestionnaireResponse.objects.update_or_create(
                submission=submission,
                questionnaire_item=item,
                reviewer_type="rm",
                defaults={"score": r["score"]}
            )

        return Response({"message": "Draft saved"})

class RMSubmitReviewView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        questionnaire_id = request.data.get("questionnaire_id")
        responses = request.data.get("responses", [])
        feedback = request.data.get("feedback")
        scope = request.data.get("scope_of_improvement")

        if not questionnaire_id:
            return Response(
                {"error": "questionnaire_id is required."},
                status=400
            )

        if not isinstance(responses, list) or not responses:
            return Response(
                {"error": "Responses cannot be empty."},
                status=400
            )

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire.objects.select_related("employee"),
            id=questionnaire_id
        )

        if questionnaire.employee.reporting_manager_id != request.user.id:
            return Response(
                {"error": "Not authorized to review this questionnaire."},
                status=403
            )

        submission, _ = EmployeeQuestionnaireStageSubmission.objects.get_or_create(
            employee_questionnaire=questionnaire,
            evaluator_type="rm",
            defaults={
                "submitted_by": request.user,
                "status": "draft",
            }
        )

        now = timezone.now()

        submission.submitted_by = request.user
        submission.feedback = feedback
        submission.scope_of_improvement = scope
        submission.status = "submitted"
        submission.submitted_at = now
        submission.save(
            update_fields=[
                "submitted_by",
                "feedback",
                "scope_of_improvement",
                "status",
                "submitted_at",
            ]
        )

        try:
            item_ids = [int(r["item_id"]) for r in responses]
        except (KeyError, TypeError, ValueError):
            return Response(
                {"error": "Each response must contain a valid item_id."},
                status=400
            )

        items = EmployeeQuestionnaireItem.objects.filter(
            id__in=item_ids,
            employee_questionnaire=questionnaire
        )

        item_map = {item.id: item for item in items}

        missing_item_ids = [item_id for item_id in item_ids if item_id not in item_map]
        if missing_item_ids:
            return Response(
                {"error": f"Invalid questionnaire item ids: {missing_item_ids}"},
                status=400
            )

        existing_responses = EmployeeQuestionnaireResponse.objects.filter(
            submission=submission,
            questionnaire_item_id__in=item_ids,
            reviewer_type="rm",
        )

        existing_map = {
            response.questionnaire_item_id: response for response in existing_responses
        }

        responses_to_update = []
        responses_to_create = []

        for r in responses:
            try:
                item_id = int(r["item_id"])
                score = int(r["score"])
            except (KeyError, TypeError, ValueError):
                return Response(
                    {"error": "Each response must contain valid item_id and score."},
                    status=400
                )

            item = item_map[item_id]
            existing = existing_map.get(item_id)

            if existing:
                existing.score = score
                existing.reviewer_type = "rm"
                responses_to_update.append(existing)
            else:
                responses_to_create.append(
                    EmployeeQuestionnaireResponse(
                        submission=submission,
                        questionnaire_item=item,
                        reviewer_type="rm",
                        score=score,
                    )
                )

        if responses_to_update:
            EmployeeQuestionnaireResponse.objects.bulk_update(
                responses_to_update,
                ["score", "reviewer_type"]
            )

        if responses_to_create:
            EmployeeQuestionnaireResponse.objects.bulk_create(responses_to_create)

        rm_band = str(request.user.band or "").upper()
        questionnaire.status = "completed" if rm_band in ["SM1", "SM2"] else "under_skip_review"
        questionnaire.save(update_fields=["status"])

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
            EmployeeQuestionnaire.objects.select_related("employee"),
            id=questionnaire_id
        )

        if questionnaire.employee.skip_level_manager != request.user:
            return Response(
                {"error": "Not authorized for this questionnaire"},
                status=403
            )

        submission = (
            EmployeeQuestionnaireStageSubmission.objects
            .filter(
                employee_questionnaire_id=questionnaire_id,
                evaluator_type="rm",
                status="submitted",
            )
            .order_by("-submitted_at", "-id")
            .first()
        )

        if not submission:
            return Response({
                "feedback": "",
                "scope_of_improvement": "",
                "responses": []
            })

        responses = (
            EmployeeQuestionnaireResponse.objects
            .filter(
                submission=submission,
                reviewer_type="rm",
            )
            .select_related(
                "questionnaire_item",
                "questionnaire_item__parameter"
            )
            .order_by("questionnaire_item__order")
        )

        data = [
            {
                "question": r.questionnaire_item.parameter.question_text,
                "score": r.score,
            }
            for r in responses
        ]

        return Response({
            "feedback": submission.feedback or "",
            "scope_of_improvement": submission.scope_of_improvement or "",
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

    @transaction.atomic
    def post(self, request):
        questionnaire_id = request.data.get("questionnaire_id")
        responses = request.data.get("responses", [])
        feedback = request.data.get("feedback")
        scope = request.data.get("scope_of_improvement")

        if not questionnaire_id:
            return Response(
                {"error": "questionnaire_id is required."},
                status=400
            )

        if not isinstance(responses, list) or not responses:
            return Response(
                {"error": "Responses cannot be empty."},
                status=400
            )

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire.objects.select_related("employee", "peer_reviewer"),
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

        now = timezone.now()

        submission.submitted_by = request.user
        submission.feedback = feedback
        submission.scope_of_improvement = scope
        submission.status = "submitted"
        submission.submitted_at = now
        submission.save(
            update_fields=[
                "submitted_by",
                "feedback",
                "scope_of_improvement",
                "status",
                "submitted_at",
            ]
        )

        try:
            item_ids = [int(r["item_id"]) for r in responses]
        except (KeyError, TypeError, ValueError):
            return Response(
                {"error": "Each response must contain a valid item_id."},
                status=400
            )

        items = EmployeeQuestionnaireItem.objects.filter(
            id__in=item_ids,
            employee_questionnaire=questionnaire
        )
        item_map = {item.id: item for item in items}

        missing_item_ids = [item_id for item_id in item_ids if item_id not in item_map]
        if missing_item_ids:
            return Response(
                {"error": f"Invalid questionnaire item ids: {missing_item_ids}"},
                status=400
            )

        existing_responses = EmployeeQuestionnaireResponse.objects.filter(
            submission=submission,
            questionnaire_item_id__in=item_ids,
            reviewer_type="skip",
        )
        existing_map = {
            response.questionnaire_item_id: response for response in existing_responses
        }

        responses_to_update = []
        responses_to_create = []

        for r in responses:
            try:
                item_id = int(r["item_id"])
                score = int(r["score"])
            except (KeyError, TypeError, ValueError):
                return Response(
                    {"error": "Each response must contain valid item_id and score."},
                    status=400
                )

            item = item_map[item_id]
            existing = existing_map.get(item_id)

            if existing:
                existing.score = score
                existing.reviewer_type = "skip"
                responses_to_update.append(existing)
            else:
                responses_to_create.append(
                    EmployeeQuestionnaireResponse(
                        submission=submission,
                        questionnaire_item=item,
                        reviewer_type="skip",
                        score=score,
                    )
                )

        if responses_to_update:
            EmployeeQuestionnaireResponse.objects.bulk_update(
                responses_to_update,
                ["score", "reviewer_type"]
            )

        if responses_to_create:
            EmployeeQuestionnaireResponse.objects.bulk_create(responses_to_create)

        peer_submission_done = EmployeeQuestionnaireStageSubmission.objects.filter(
            employee_questionnaire=questionnaire,
            evaluator_type="peer",
            status="submitted"
        ).exists()

        if questionnaire.peer_reviewer:
            questionnaire.status = "completed" if peer_submission_done else "skip_reviewed"
        else:
            questionnaire.status = "completed"

        questionnaire.save(update_fields=["status"])

        return Response({"message": "Skip review submitted successfully"})

class PeerEmployeeSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        User = get_user_model()

        query = request.query_params.get("q", "").strip()

        employees = User.objects.filter(
            is_active=True
        ).exclude(
            id=request.user.id
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

        if peer.id == request.user.id:
            return Response(
                {"error": "You cannot recommend yourself as peer reviewer."},
                status=400
            )

        questionnaire.peer_reviewer = peer
        questionnaire.peer_requested_at = timezone.now()
        questionnaire.save(update_fields=["peer_reviewer", "peer_requested_at"])

        return Response({"message": "Peer review request sent successfully"})

class PeerPendingReviewsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        peer = request.user

        questionnaires = (
            EmployeeQuestionnaire.objects
            .filter(peer_reviewer=peer)
            .exclude(status="draft")
            .select_related("employee", "review_cycle")
            .order_by("-id")
        )

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
                "peer_completed": peer_submission,
                "status": q.status,
                "peer_requested_at": q.peer_requested_at,
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

    @transaction.atomic
    def post(self, request):
        questionnaire_id = request.data.get("questionnaire_id")
        responses = request.data.get("responses", [])
        feedback = request.data.get("feedback")
        scope = request.data.get("scope_of_improvement")

        if not questionnaire_id:
            return Response(
                {"error": "questionnaire_id is required."},
                status=400
            )

        if not isinstance(responses, list) or not responses:
            return Response(
                {"error": "Responses cannot be empty."},
                status=400
            )

        questionnaire = get_object_or_404(
            EmployeeQuestionnaire.objects.select_related("peer_reviewer"),
            id=questionnaire_id
        )

        if questionnaire.peer_reviewer != request.user:
            return Response({"error": "Not authorized"}, status=403)

        submission, _ = EmployeeQuestionnaireStageSubmission.objects.get_or_create(
            employee_questionnaire=questionnaire,
            evaluator_type="peer",
            defaults={
                "submitted_by": request.user,
                "status": "draft",
            }
        )

        now = timezone.now()

        submission.submitted_by = request.user
        submission.feedback = feedback
        submission.scope_of_improvement = scope
        submission.status = "submitted"
        submission.submitted_at = now
        submission.save(
            update_fields=[
                "submitted_by",
                "feedback",
                "scope_of_improvement",
                "status",
                "submitted_at",
            ]
        )

        try:
            item_ids = [int(r["item_id"]) for r in responses]
        except (KeyError, TypeError, ValueError):
            return Response(
                {"error": "Each response must contain a valid item_id."},
                status=400
            )

        items = EmployeeQuestionnaireItem.objects.filter(
            id__in=item_ids,
            employee_questionnaire=questionnaire
        )
        item_map = {item.id: item for item in items}

        missing_item_ids = [item_id for item_id in item_ids if item_id not in item_map]
        if missing_item_ids:
            return Response(
                {"error": f"Invalid questionnaire item ids: {missing_item_ids}"},
                status=400
            )

        existing_responses = EmployeeQuestionnaireResponse.objects.filter(
            submission=submission,
            questionnaire_item_id__in=item_ids,
            reviewer_type="peer",
        )
        existing_map = {
            response.questionnaire_item_id: response for response in existing_responses
        }

        responses_to_update = []
        responses_to_create = []

        for r in responses:
            try:
                item_id = int(r["item_id"])
                score = int(r["score"])
            except (KeyError, TypeError, ValueError):
                return Response(
                    {"error": "Each response must contain valid item_id and score."},
                    status=400
                )

            item = item_map[item_id]
            existing = existing_map.get(item_id)

            if existing:
                existing.score = score
                existing.reviewer_type = "peer"
                responses_to_update.append(existing)
            else:
                responses_to_create.append(
                    EmployeeQuestionnaireResponse(
                        submission=submission,
                        questionnaire_item=item,
                        reviewer_type="peer",
                        score=score,
                    )
                )

        if responses_to_update:
            EmployeeQuestionnaireResponse.objects.bulk_update(
                responses_to_update,
                ["score", "reviewer_type"]
            )

        if responses_to_create:
            EmployeeQuestionnaireResponse.objects.bulk_create(responses_to_create)

        skip_submission_done = EmployeeQuestionnaireStageSubmission.objects.filter(
            employee_questionnaire=questionnaire,
            evaluator_type="skip",
            status="submitted"
        ).exists()

        if skip_submission_done or questionnaire.status == "skip_reviewed":
            questionnaire.status = "completed"
            questionnaire.save(update_fields=["status"])

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