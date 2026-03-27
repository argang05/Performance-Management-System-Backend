from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.db.models import Q
from django.shortcuts import get_object_or_404

from evaluations.models import QuestionCategory, QuestionParameter
from admin_console.serializers import (
    QuestionCategorySerializer,
    QuestionParameterListSerializer,
    QuestionParameterCreateUpdateSerializer,
)


def is_admin_user(user):
    return str(getattr(user, "employee_number", "")) == "100607"


class AdminQuestionCategoryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_admin_user(request.user):
            return Response({"error": "Not authorized"}, status=403)

        categories = QuestionCategory.objects.all().order_by("category_type", "name")
        serializer = QuestionCategorySerializer(categories, many=True)
        return Response({"results": serializer.data})


class AdminQuestionListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_admin_user(request.user):
            return Response({"error": "Not authorized"}, status=403)

        search = request.query_params.get("search", "").strip()
        category_type = request.query_params.get("category_type", "").strip()
        department = request.query_params.get("department", "").strip()
        is_active = request.query_params.get("is_active", "").strip()

        queryset = QuestionParameter.objects.select_related("category").all().order_by("id")

        if search:
            queryset = queryset.filter(
                Q(question_text__icontains=search) |
                Q(category__name__icontains=search) |
                Q(department__icontains=search)
            )

        if category_type:
            queryset = queryset.filter(category__category_type=category_type)

        if department:
            if department.lower() == "common":
                queryset = queryset.filter(department__isnull=True)
            else:
                queryset = queryset.filter(department=department)

        if is_active.lower() in ["true", "false"]:
            queryset = queryset.filter(is_active=(is_active.lower() == "true"))

        serializer = QuestionParameterListSerializer(queryset, many=True)
        return Response({"results": serializer.data})

    def post(self, request):
        if not is_admin_user(request.user):
            return Response({"error": "Not authorized"}, status=403)

        serializer = QuestionParameterCreateUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        question = serializer.save()
        response_serializer = QuestionParameterListSerializer(question)

        return Response(
            {
                "message": "Question created successfully.",
                "question": response_serializer.data,
            },
            status=201,
        )


class AdminQuestionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, question_id):
        if not is_admin_user(request.user):
            return Response({"error": "Not authorized"}, status=403)

        question = get_object_or_404(QuestionParameter, id=question_id)

        serializer = QuestionParameterCreateUpdateSerializer(
            question,
            data=request.data,
            partial=True,
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        updated_question = serializer.save()
        response_serializer = QuestionParameterListSerializer(updated_question)

        return Response({
            "message": "Question updated successfully.",
            "question": response_serializer.data,
        })

    def delete(self, request, question_id):
        if not is_admin_user(request.user):
            return Response({"error": "Not authorized"}, status=403)

        question = get_object_or_404(QuestionParameter, id=question_id)

        question.is_active = False
        question.save(update_fields=["is_active"])

        return Response({
            "message": "Question deactivated successfully."
        })