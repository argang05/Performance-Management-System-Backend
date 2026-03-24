from django.db import models
from django.conf import settings
from evaluations.models import EmployeeQuestionnaire

Employee = settings.AUTH_USER_MODEL


class ScoreConfiguration(models.Model):

    name = models.CharField(max_length=100, default="Default Configuration")

    behavioural_weight = models.FloatField(default=0.40)
    performance_weight = models.FloatField(default=0.60)

    self_weight = models.FloatField(default=0.10)
    rm_weight = models.FloatField(default=0.50)
    skip_weight = models.FloatField(default=0.25)
    peer_weight = models.FloatField(default=0.15)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class EmployeePerformanceScore(models.Model):

    employee_questionnaire = models.OneToOneField(
        EmployeeQuestionnaire,
        on_delete=models.CASCADE
    )

    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE
    )

    review_cycle = models.ForeignKey(
        "evaluations.ReviewCycle",
        on_delete=models.CASCADE
    )

    # -----------------------------
    # Category scores
    # -----------------------------

    self_behavioural_score = models.FloatField(null=True, blank=True)
    self_performance_score = models.FloatField(null=True, blank=True)

    rm_behavioural_score = models.FloatField(null=True, blank=True)
    rm_performance_score = models.FloatField(null=True, blank=True)

    skip_behavioural_score = models.FloatField(null=True, blank=True)
    skip_performance_score = models.FloatField(null=True, blank=True)

    peer_behavioural_score = models.FloatField(null=True, blank=True)
    peer_performance_score = models.FloatField(null=True, blank=True)

    # -----------------------------
    # Evaluator scores
    # -----------------------------

    self_score = models.FloatField(null=True, blank=True)
    rm_score = models.FloatField(null=True, blank=True)
    skip_score = models.FloatField(null=True, blank=True)
    peer_score = models.FloatField(null=True, blank=True)

    # -----------------------------
    # Effective weights used
    # -----------------------------

    effective_self_weight = models.FloatField(null=True, blank=True)
    effective_rm_weight = models.FloatField(null=True, blank=True)
    effective_skip_weight = models.FloatField(null=True, blank=True)
    effective_peer_weight = models.FloatField(null=True, blank=True)

    # -----------------------------
    # Final score
    # -----------------------------

    system_final_score = models.FloatField(null=True, blank=True)

    hr_override_score = models.FloatField(null=True, blank=True)
    final_effective_score = models.FloatField(null=True, blank=True)

    override_reason = models.TextField(null=True, blank=True)

    overridden_by = models.ForeignKey(
        "employees.Employee",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="score_overrides"
    )

    overridden_at = models.DateTimeField(null=True, blank=True)

    # -----------------------------
    # Release control
    # -----------------------------

    is_released_to_employee = models.BooleanField(default=False)

    released_by = models.ForeignKey(
        "employees.Employee",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="released_scores"
    )

    released_at = models.DateTimeField(null=True, blank=True)

    calculated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee} - Score"