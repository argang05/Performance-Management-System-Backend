from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.shortcuts import get_object_or_404
from django.db import transaction

from evaluations.models import ReviewCycle
from admin_console.serializers import ReviewCycleSerializer


def is_admin_user(user):
    return str(getattr(user, "employee_number", "")) == "100607"


class AdminReviewCycleListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_admin_user(request.user):
            return Response({"error": "Not authorized"}, status=403)

        queryset = ReviewCycle.objects.all().order_by("-start_date", "-id")
        serializer = ReviewCycleSerializer(queryset, many=True)
        return Response({"results": serializer.data})

    def post(self, request):
        if not is_admin_user(request.user):
            return Response({"error": "Not authorized"}, status=403)

        serializer = ReviewCycleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        start_date = serializer.validated_data["start_date"]
        end_date = serializer.validated_data["end_date"]

        if end_date < start_date:
            return Response(
                {"error": "End date cannot be earlier than start date."},
                status=400,
            )

        instance = serializer.save()
        return Response(
            {
                "message": "Review cycle created successfully.",
                "cycle": ReviewCycleSerializer(instance).data,
            },
            status=201,
        )


class AdminReviewCycleDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, cycle_id):
        if not is_admin_user(request.user):
            return Response({"error": "Not authorized"}, status=403)

        instance = get_object_or_404(ReviewCycle, id=cycle_id)

        serializer = ReviewCycleSerializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        start_date = serializer.validated_data.get("start_date", instance.start_date)
        end_date = serializer.validated_data.get("end_date", instance.end_date)

        if end_date < start_date:
            return Response(
                {"error": "End date cannot be earlier than start date."},
                status=400,
            )

        serializer.save()
        return Response({
            "message": "Review cycle updated successfully.",
            "cycle": serializer.data,
        })


class AdminReviewCycleActivateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def put(self, request, cycle_id):
        if not is_admin_user(request.user):
            return Response({"error": "Not authorized"}, status=403)

        target = get_object_or_404(ReviewCycle, id=cycle_id)

        ReviewCycle.objects.filter(is_active=True).exclude(id=target.id).update(is_active=False)
        target.is_active = True
        target.save(update_fields=["is_active"])

        return Response({
            "message": "Review cycle activated successfully."
        })