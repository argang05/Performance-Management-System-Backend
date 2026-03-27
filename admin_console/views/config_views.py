from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.shortcuts import get_object_or_404
from django.db import transaction

from scoring.models import (
    ScoreConfiguration,
    PotentialScoreConfiguration,
    AppraisalRecommendationConfig,
)
from admin_console.serializers import (
    ScoreConfigurationSerializer,
    PotentialScoreConfigurationSerializer,
    AppraisalRecommendationConfigSerializer,
)


def is_admin_user(user):
    return str(getattr(user, "employee_number", "")) == "100607"


class AdminScoreConfigurationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_admin_user(request.user):
            return Response({"error": "Not authorized"}, status=403)

        queryset = ScoreConfiguration.objects.all().order_by("-created_at")
        serializer = ScoreConfigurationSerializer(queryset, many=True)
        return Response({"results": serializer.data})

    def post(self, request):
        if not is_admin_user(request.user):
            return Response({"error": "Not authorized"}, status=403)

        serializer = ScoreConfigurationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        instance = serializer.save()
        return Response(
            {
                "message": "Score configuration created successfully.",
                "configuration": ScoreConfigurationSerializer(instance).data,
            },
            status=201,
        )


class AdminScoreConfigurationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, config_id):
        if not is_admin_user(request.user):
            return Response({"error": "Not authorized"}, status=403)

        instance = get_object_or_404(ScoreConfiguration, id=config_id)

        serializer = ScoreConfigurationSerializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        serializer.save()
        return Response({
            "message": "Score configuration updated successfully.",
            "configuration": serializer.data,
        })


class AdminScoreConfigurationActivateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def put(self, request, config_id):
        if not is_admin_user(request.user):
            return Response({"error": "Not authorized"}, status=403)

        target = get_object_or_404(ScoreConfiguration, id=config_id)

        ScoreConfiguration.objects.filter(is_active=True).update(is_active=False)
        target.is_active = True
        target.save(update_fields=["is_active"])

        return Response({
            "message": "Score configuration activated successfully."
        })


class AdminPotentialConfigurationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_admin_user(request.user):
            return Response({"error": "Not authorized"}, status=403)

        queryset = PotentialScoreConfiguration.objects.all().order_by("-created_at")
        serializer = PotentialScoreConfigurationSerializer(queryset, many=True)
        return Response({"results": serializer.data})

    def post(self, request):
        if not is_admin_user(request.user):
            return Response({"error": "Not authorized"}, status=403)

        serializer = PotentialScoreConfigurationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        instance = serializer.save()
        return Response(
            {
                "message": "Potential configuration created successfully.",
                "configuration": PotentialScoreConfigurationSerializer(instance).data,
            },
            status=201,
        )


class AdminPotentialConfigurationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, config_id):
        if not is_admin_user(request.user):
            return Response({"error": "Not authorized"}, status=403)

        instance = get_object_or_404(PotentialScoreConfiguration, id=config_id)

        serializer = PotentialScoreConfigurationSerializer(
            instance,
            data=request.data,
            partial=True,
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        serializer.save()
        return Response({
            "message": "Potential configuration updated successfully.",
            "configuration": serializer.data,
        })


class AdminPotentialConfigurationActivateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def put(self, request, config_id):
        if not is_admin_user(request.user):
            return Response({"error": "Not authorized"}, status=403)

        target = get_object_or_404(PotentialScoreConfiguration, id=config_id)

        PotentialScoreConfiguration.objects.filter(is_active=True).update(is_active=False)
        target.is_active = True
        target.save(update_fields=["is_active"])

        return Response({
            "message": "Potential configuration activated successfully."
        })


class AdminAppraisalConfigurationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_admin_user(request.user):
            return Response({"error": "Not authorized"}, status=403)

        queryset = AppraisalRecommendationConfig.objects.all().order_by("box_label")
        serializer = AppraisalRecommendationConfigSerializer(queryset, many=True)
        return Response({"results": serializer.data})

    def post(self, request):
        if not is_admin_user(request.user):
            return Response({"error": "Not authorized"}, status=403)

        serializer = AppraisalRecommendationConfigSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        instance = serializer.save()
        return Response(
            {
                "message": "Appraisal configuration created successfully.",
                "configuration": AppraisalRecommendationConfigSerializer(instance).data,
            },
            status=201,
        )


class AdminAppraisalConfigurationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, config_id):
        if not is_admin_user(request.user):
            return Response({"error": "Not authorized"}, status=403)

        instance = get_object_or_404(AppraisalRecommendationConfig, id=config_id)

        serializer = AppraisalRecommendationConfigSerializer(
            instance,
            data=request.data,
            partial=True,
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        serializer.save()
        return Response({
            "message": "Appraisal configuration updated successfully.",
            "configuration": serializer.data,
        })