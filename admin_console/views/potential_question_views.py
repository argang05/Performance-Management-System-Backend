from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.db.models import Q
from django.shortcuts import get_object_or_404

from scoring.models import PotentialParameter
from admin_console.serializers import (
    PotentialParameterListSerializer,
    PotentialParameterCreateUpdateSerializer,
)


def is_admin_user(user):
    return str(getattr(user, "employee_number", "")) == "100607"


class AdminPotentialQuestionListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_admin_user(request.user):
            return Response({"error": "Not authorized"}, status=403)

        search = request.query_params.get("search", "").strip()
        is_active = request.query_params.get("is_active", "").strip()

        queryset = PotentialParameter.objects.all().order_by("id")

        if search:
            queryset = queryset.filter(
                Q(question_text__icontains=search)
            )

        if is_active.lower() in ["true", "false"]:
            queryset = queryset.filter(is_active=(is_active.lower() == "true"))

        serializer = PotentialParameterListSerializer(queryset, many=True)
        return Response({"results": serializer.data})

    def post(self, request):
        if not is_admin_user(request.user):
            return Response({"error": "Not authorized"}, status=403)

        serializer = PotentialParameterCreateUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        potential_question = serializer.save()
        response_serializer = PotentialParameterListSerializer(potential_question)

        return Response(
            {
                "message": "Potential question created successfully.",
                "question": response_serializer.data,
            },
            status=201,
        )


class AdminPotentialQuestionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, question_id):
        if not is_admin_user(request.user):
            return Response({"error": "Not authorized"}, status=403)

        potential_question = get_object_or_404(PotentialParameter, id=question_id)

        serializer = PotentialParameterCreateUpdateSerializer(
            potential_question,
            data=request.data,
            partial=True,
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        updated_question = serializer.save()
        response_serializer = PotentialParameterListSerializer(updated_question)

        return Response({
            "message": "Potential question updated successfully.",
            "question": response_serializer.data,
        })

    def delete(self, request, question_id):
        if not is_admin_user(request.user):
            return Response({"error": "Not authorized"}, status=403)

        potential_question = get_object_or_404(PotentialParameter, id=question_id)

        potential_question.is_active = False
        potential_question.save(update_fields=["is_active"])

        return Response({
            "message": "Potential question deactivated successfully."
        })