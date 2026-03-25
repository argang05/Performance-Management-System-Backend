from django.utils import timezone

from evaluations.models import EmployeeQuestionnaireStageSubmission
from scoring.models import (
    EmployeeAnalyticsRelease,
    EmployeePerformanceScore,
    EmployeePastPerformanceIndex,
    EmployeePotentialScore,
    EmployeeNineBoxPlacement,
)


def get_or_create_analytics_release(questionnaire):
    analytics_release, _ = EmployeeAnalyticsRelease.objects.get_or_create(
        employee_questionnaire=questionnaire
    )
    return analytics_release


def get_analytics_readiness(questionnaire):
    missing_requirements = []

    has_processed_score = EmployeePerformanceScore.objects.filter(
        employee_questionnaire=questionnaire,
        final_effective_score__isnull=False,
    ).exists()

    if not has_processed_score:
        missing_requirements.append("Processed performance score not available.")

    has_ppi = EmployeePastPerformanceIndex.objects.filter(
        employee=questionnaire.employee,
        review_cycle=questionnaire.review_cycle,
    ).exists()

    if not has_ppi:
        missing_requirements.append("PPI not available.")

    has_potential = EmployeePotentialScore.objects.filter(
        employee_questionnaire=questionnaire,
        final_potential_score__isnull=False,
    ).exists()

    if not has_potential:
        missing_requirements.append("Potential score not available.")

    has_nine_box = EmployeeNineBoxPlacement.objects.filter(
        employee_questionnaire=questionnaire
    ).exists()

    if not has_nine_box:
        missing_requirements.append("9-box placement not available.")

    stage_rows = EmployeeQuestionnaireStageSubmission.objects.filter(
        employee_questionnaire=questionnaire
    ).values("evaluator_type", "status")

    submitted_map = {
        row["evaluator_type"]: row["status"] == "submitted"
        for row in stage_rows
    }

    if not submitted_map.get("self", False):
        missing_requirements.append("Self feedback not submitted.")

    if not submitted_map.get("rm", False):
        missing_requirements.append("RM feedback not submitted.")

    if not submitted_map.get("skip", False):
        missing_requirements.append("Skip feedback not submitted.")

    # Peer optional for now

    return {
        "is_ready": len(missing_requirements) == 0,
        "missing_requirements": missing_requirements,
        "has_processed_score": has_processed_score,
        "has_ppi": has_ppi,
        "has_potential": has_potential,
        "has_nine_box": has_nine_box,
        "has_self_feedback": submitted_map.get("self", False),
        "has_rm_feedback": submitted_map.get("rm", False),
        "has_skip_feedback": submitted_map.get("skip", False),
        "has_peer_feedback": submitted_map.get("peer", False),
    }


def release_analytics_to_employee(questionnaire, hr_user):
    analytics_release = get_or_create_analytics_release(questionnaire)
    readiness = get_analytics_readiness(questionnaire)

    if not readiness["is_ready"]:
        return {
            "success": False,
            "message": "Analytics data is not ready for release.",
            "missing_requirements": readiness["missing_requirements"],
        }

    analytics_release.is_released_to_employee = True
    analytics_release.released_at = timezone.now()
    analytics_release.released_by = hr_user
    analytics_release.save()

    return {
        "success": True,
        "message": "Analytics data released successfully.",
        "missing_requirements": [],
    }


def unrelease_analytics_to_employee(questionnaire, hr_user):
    analytics_release = get_or_create_analytics_release(questionnaire)

    analytics_release.is_released_to_employee = False
    analytics_release.unreleased_at = timezone.now()
    analytics_release.unreleased_by = hr_user
    analytics_release.save()

    return {
        "success": True,
        "message": "Analytics data unreleased successfully.",
    }


def _resolve_submission_evaluator_name(submission, questionnaire):
    if submission.evaluator_type == "self":
        return (
            getattr(questionnaire.employee, "full_name", None)
            or getattr(questionnaire.employee, "first_name", None)
            or "Self"
        )

    if submission.submitted_by:
        return (
            getattr(submission.submitted_by, "full_name", None)
            or getattr(submission.submitted_by, "first_name", None)
            or str(submission.submitted_by)
        )

    if submission.evaluator_type == "rm":
        return "Reporting Manager"

    if submission.evaluator_type == "skip":
        return "Skip-Level Manager"

    if submission.evaluator_type == "peer":
        return (
            getattr(questionnaire.peer_reviewer, "full_name", None)
            or getattr(questionnaire.peer_reviewer, "first_name", None)
            or "Peer Reviewer"
        )

    return submission.evaluator_type.title()

def build_employee_analytics_report(questionnaire):
    analytics_release = get_or_create_analytics_release(questionnaire)

    score_obj = EmployeePerformanceScore.objects.filter(
        employee_questionnaire=questionnaire
    ).first()

    ppi_obj = EmployeePastPerformanceIndex.objects.filter(
        employee=questionnaire.employee,
        review_cycle=questionnaire.review_cycle,
    ).first()

    potential_obj = EmployeePotentialScore.objects.filter(
        employee_questionnaire=questionnaire
    ).first()

    nine_box_obj = EmployeeNineBoxPlacement.objects.filter(
        employee_questionnaire=questionnaire
    ).first()

    submissions = EmployeeQuestionnaireStageSubmission.objects.filter(
        employee_questionnaire=questionnaire,
        status="submitted"
    ).order_by("submitted_at")

    feedback_sections = []

    for submission in submissions:
        evaluator_type = submission.evaluator_type

        if evaluator_type == "self" and not analytics_release.show_self_feedback:
            continue
        if evaluator_type == "rm" and not analytics_release.show_rm_feedback:
            continue
        if evaluator_type == "skip" and not analytics_release.show_skip_feedback:
            continue
        if evaluator_type == "peer" and not analytics_release.show_peer_feedback:
            continue

        show_scope = True
        if evaluator_type == "self":
            show_scope = analytics_release.show_self_scope_of_improvement
        elif evaluator_type == "rm":
            show_scope = analytics_release.show_rm_scope_of_improvement
        elif evaluator_type == "skip":
            show_scope = analytics_release.show_skip_scope_of_improvement
        elif evaluator_type == "peer":
            show_scope = analytics_release.show_peer_scope_of_improvement

        feedback_sections.append({
            "role": evaluator_type,
            "evaluator_name": _resolve_submission_evaluator_name(submission, questionnaire),
            "submitted_at": submission.submitted_at,
            "feedback": submission.feedback,
            "scope_of_improvement": (
                submission.scope_of_improvement if show_scope else None
            ),
        })

    return {
        "employee_name": getattr(questionnaire.employee, "full_name", None) or getattr(
            questionnaire.employee, "first_name", ""
        ),
        "employee_number": getattr(questionnaire.employee, "employee_number", None),
        "review_cycle": getattr(questionnaire.review_cycle, "name", str(questionnaire.review_cycle)),

        "performance_score": {
            "system_final_score": (
                score_obj.system_final_score
                if score_obj and analytics_release.show_performance_score else None
            ),
            "hr_override_score": (
                score_obj.hr_override_score
                if score_obj and analytics_release.show_performance_score else None
            ),
            "final_effective_score": (
                score_obj.final_effective_score
                if score_obj and analytics_release.show_performance_score else None
            ),
        },

        "ppi": {
            "current_cycle_score": (
                ppi_obj.current_cycle_score
                if ppi_obj and analytics_release.show_ppi else None
            ),
            "previous_cycle_score_1": (
                ppi_obj.previous_cycle_score_1
                if ppi_obj and analytics_release.show_ppi else None
            ),
            "previous_cycle_score_2": (
                ppi_obj.previous_cycle_score_2
                if ppi_obj and analytics_release.show_ppi else None
            ),
            "ppi_score": (
                ppi_obj.ppi_score
                if ppi_obj and analytics_release.show_ppi else None
            ),
        },

        "potential": {
            "rm_score": (
                potential_obj.rm_score
                if potential_obj and analytics_release.show_potential_score else None
            ),
            "skip_score": (
                potential_obj.skip_score
                if potential_obj and analytics_release.show_potential_score else None
            ),
            "final_potential_score": (
                potential_obj.final_potential_score
                if potential_obj and analytics_release.show_potential_score else None
            ),
        },

        "nine_box": {
            "box_label": (
                nine_box_obj.box_label
                if nine_box_obj and analytics_release.show_nine_box else None
            ),
            "box_description": (
                nine_box_obj.box_description
                if nine_box_obj and analytics_release.show_nine_box else None
            ),
            "performance_bucket": (
                nine_box_obj.performance_bucket
                if nine_box_obj and analytics_release.show_nine_box else None
            ),
            "potential_bucket": (
                nine_box_obj.potential_bucket
                if nine_box_obj and analytics_release.show_nine_box else None
            ),
            "ppi_score": (
                nine_box_obj.ppi_score
                if nine_box_obj and analytics_release.show_nine_box else None
            ),
            "potential_score": (
                nine_box_obj.potential_score
                if nine_box_obj and analytics_release.show_nine_box else None
            ),
        },

        "feedback_sections": feedback_sections,

        "release_metadata": {
            "is_released_to_employee": analytics_release.is_released_to_employee,
            "released_at": analytics_release.released_at,
        },
    }