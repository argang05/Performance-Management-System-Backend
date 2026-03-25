from django.utils import timezone

from scoring.models import (
    AppraisalRecommendationConfig,
    EmployeeAppraisalRecommendation,
    EmployeeNineBoxPlacement,
)


def generate_appraisal_recommendation(employee_questionnaire):
    """
    Generate appraisal recommendation based on:
    - 9-box placement
    - PPI score
    - Potential score
    - configurable appraisal ranges
    """

    # ---------------------------------------------------
    # Step 1 — Fetch 9-box placement
    # ---------------------------------------------------

    nine_box = EmployeeNineBoxPlacement.objects.get(
        employee_questionnaire=employee_questionnaire
    )

    box_label = nine_box.box_label
    ppi_score = nine_box.ppi_score
    potential_score = nine_box.potential_score

    # ---------------------------------------------------
    # Step 2 — Fetch config range
    # ---------------------------------------------------

    config = AppraisalRecommendationConfig.objects.get(
        box_label=box_label,
        is_active=True
    )

    min_percent = config.min_percent
    max_percent = config.max_percent

    # ---------------------------------------------------
    # Step 3 — Normalize scores
    # ---------------------------------------------------

    normalized_ppi = ppi_score / 10
    normalized_potential = potential_score / 10

    position_factor = (normalized_ppi + normalized_potential) / 2

    # ---------------------------------------------------
    # Step 4 — Calculate suggested appraisal %
    # ---------------------------------------------------

    suggested_percent = min_percent + (
        (max_percent - min_percent) * position_factor
    )

    suggested_percent = round(suggested_percent, 2)

    # ---------------------------------------------------
    # Step 5 — Store / update recommendation
    # ---------------------------------------------------

    recommendation, created = EmployeeAppraisalRecommendation.objects.update_or_create(
        employee_questionnaire=employee_questionnaire,
        defaults={
            "employee": employee_questionnaire.employee,
            "review_cycle": employee_questionnaire.review_cycle,
            "nine_box_placement": nine_box,

            "ppi_score_used": ppi_score,
            "potential_score_used": potential_score,

            "box_label": box_label,

            "min_appraisal_percent": min_percent,
            "max_appraisal_percent": max_percent,

            "suggested_appraisal_percent": suggested_percent,

            "final_effective_appraisal_percent": suggested_percent,

            "calculated_at": timezone.now(),
        }
    )

    return recommendation


def apply_hr_override(recommendation, override_percent, reason, hr_employee):
    """
    Apply HR override to appraisal recommendation
    """

    recommendation.hr_override_percent = override_percent
    recommendation.override_reason = reason

    recommendation.overridden_by = hr_employee
    recommendation.overridden_at = timezone.now()

    recommendation.final_effective_appraisal_percent = override_percent

    recommendation.save()

    return recommendation


def get_appraisal_recommendation(employee_questionnaire):
    """
    Fetch stored appraisal recommendation
    """

    return EmployeeAppraisalRecommendation.objects.get(
        employee_questionnaire=employee_questionnaire
    )