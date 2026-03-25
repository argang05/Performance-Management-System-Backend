from .models import EmployeePastPerformanceIndex
from .models import EmployeePerformanceScore


def get_past_scores(employee, current_cycle):
    """
    Fetch past performance scores for employee
    ordered from latest to oldest.
    """

    scores = EmployeePerformanceScore.objects.filter(
        employee=employee,
        review_cycle__id__lt=current_cycle.id
    ).order_by("-review_cycle__id")

    past_scores = []

    for s in scores:
        if s.final_effective_score is not None:
            past_scores.append(s.final_effective_score)

    return past_scores

def calculate_ppi_score(current_score, past_scores):
    """
    PPI calculation logic based on available history.
    """

    if not past_scores:
        return round(current_score, 2)

    if len(past_scores) == 1:
        p1 = past_scores[0]

        ppi = (
            p1 * 0.4 +
            current_score * 0.6
        )

        return round(ppi, 2)

    # Use latest two past scores
    p1 = past_scores[0]
    p2 = past_scores[1]

    ppi = (
        p2 * 0.2 +
        p1 * 0.3 +
        current_score * 0.5
    )

    return round(ppi, 2)

def save_ppi(employee, cycle, current_score, past_scores):

    prev1 = past_scores[0] if len(past_scores) >= 1 else None
    prev2 = past_scores[1] if len(past_scores) >= 2 else None

    ppi = calculate_ppi_score(current_score, past_scores)

    obj, _ = EmployeePastPerformanceIndex.objects.update_or_create(
        employee=employee,
        review_cycle=cycle,
        defaults={
            "current_cycle_score": current_score,
            "previous_cycle_score_1": prev1,
            "previous_cycle_score_2": prev2,
            "ppi_score": ppi
        }
    )

    return obj