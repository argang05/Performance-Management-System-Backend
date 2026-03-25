from .models import EmployeeNineBoxPlacement


PERFORMANCE_BUCKET_LOW = "low"
PERFORMANCE_BUCKET_MEDIUM = "medium"
PERFORMANCE_BUCKET_HIGH = "high"

POTENTIAL_BUCKET_LOW = "low"
POTENTIAL_BUCKET_MEDIUM = "medium"
POTENTIAL_BUCKET_HIGH = "high"


NINE_BOX_LABEL_MAP = {
    ("high", "low"): "Star",
    ("high", "medium"): "Future Leader",
    ("high", "high"): "Top Talent",

    ("medium", "low"): "Core",
    ("medium", "medium"): "Growth",
    ("medium", "high"): "High Potential",

    ("low", "low"): "Risk",
    ("low", "medium"): "Inconsistent",
    ("low", "high"): "Misaligned",
}


NINE_BOX_DESCRIPTION_MAP = {
    "Star": (
        "High performance with lower future potential. "
        "A strong and dependable contributor who delivers excellent results in the current role."
    ),
    "Future Leader": (
        "High performance with medium potential. "
        "Shows strong results today and has growing readiness for larger responsibilities."
    ),
    "Top Talent": (
        "High performance with high potential. "
        "A top-tier employee with strong current delivery and excellent future readiness."
    ),
    "Core": (
        "Medium performance with lower potential. "
        "A stable contributor who performs reliably in the current role."
    ),
    "Growth": (
        "Medium performance with medium potential. "
        "Shows steady contribution and can grow further with support and development."
    ),
    "High Potential": (
        "Medium performance with high potential. "
        "Shows strong future readiness and can move to higher impact with better execution consistency."
    ),
    "Risk": (
        "Low performance with low potential. "
        "Needs close support, performance intervention, and role-fit review."
    ),
    "Inconsistent": (
        "Low performance with medium potential. "
        "Shows mixed signals and needs structured coaching to improve consistency."
    ),
    "Misaligned": (
        "Low performance with high potential. "
        "Has future capability indicators but current performance suggests role or execution misalignment."
    ),
}


def get_performance_bucket(ppi_score):
    if ppi_score is None:
        return None

    if ppi_score < 4:
        return PERFORMANCE_BUCKET_LOW

    if ppi_score < 7:
        return PERFORMANCE_BUCKET_MEDIUM

    return PERFORMANCE_BUCKET_HIGH


def get_potential_bucket(potential_score):
    if potential_score is None:
        return None

    if potential_score < 4:
        return POTENTIAL_BUCKET_LOW

    if potential_score < 7:
        return POTENTIAL_BUCKET_MEDIUM

    return POTENTIAL_BUCKET_HIGH


def get_nine_box_label(performance_bucket, potential_bucket):
    if not performance_bucket or not potential_bucket:
        return None

    return NINE_BOX_LABEL_MAP.get((performance_bucket, potential_bucket))


def get_nine_box_description(box_label):
    if not box_label:
        return None

    return NINE_BOX_DESCRIPTION_MAP.get(box_label)


def build_nine_box_result(ppi_score, potential_score):
    performance_bucket = get_performance_bucket(ppi_score)
    potential_bucket = get_potential_bucket(potential_score)

    box_label = get_nine_box_label(
        performance_bucket=performance_bucket,
        potential_bucket=potential_bucket
    )

    box_description = get_nine_box_description(box_label)

    return {
        "ppi_score": round(ppi_score, 2) if ppi_score is not None else None,
        "potential_score": round(potential_score, 2) if potential_score is not None else None,
        "performance_bucket": performance_bucket,
        "potential_bucket": potential_bucket,
        "box_label": box_label,
        "box_description": box_description,
    }


def save_nine_box_placement(employee, review_cycle, employee_questionnaire, ppi_score, potential_score):
    payload = build_nine_box_result(
        ppi_score=ppi_score,
        potential_score=potential_score
    )

    placement, _ = EmployeeNineBoxPlacement.objects.update_or_create(
        employee_questionnaire=employee_questionnaire,
        defaults={
            "employee": employee,
            "review_cycle": review_cycle,
            "ppi_score": payload["ppi_score"],
            "potential_score": payload["potential_score"],
            "performance_bucket": payload["performance_bucket"],
            "potential_bucket": payload["potential_bucket"],
            "box_label": payload["box_label"],
            "box_description": payload["box_description"],
        }
    )

    return placement