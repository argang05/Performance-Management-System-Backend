from evaluations.models import (
    EmployeeQuestionnaireStageSubmission,
    EmployeeQuestionnaireResponse,
)

from .models import ScoreConfiguration


def get_active_config():
    return ScoreConfiguration.objects.filter(is_active=True).first()


def weighted_category_score(responses):

    total_weight = 0
    weighted_sum = 0

    for r in responses:
        weight = r.questionnaire_item.weightage
        weighted_sum += r.score * weight
        total_weight += weight

    if total_weight == 0:
        return None

    return round(weighted_sum / total_weight, 2)


def calculate_evaluator_score(behavioural, performance, config):

    if behavioural is None or performance is None:
        return None

    score = (
        behavioural * config.behavioural_weight +
        performance * config.performance_weight
    )

    return round(score, 2)


def normalize_weights(active_evaluators, config):

    weights = {
        "self": config.self_weight,
        "rm": config.rm_weight,
        "skip": config.skip_weight,
        "peer": config.peer_weight,
    }

    active_total = sum(weights[e] for e in active_evaluators)

    normalized = {}

    for e in active_evaluators:
        normalized[e] = weights[e] / active_total

    return normalized


def calculate_final_score(scores, weights):

    final = 0

    for evaluator in scores:
        if scores[evaluator] is not None:
            final += scores[evaluator] * weights[evaluator]

    return round(final, 2)