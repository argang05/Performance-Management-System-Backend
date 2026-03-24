from django.db import models
from django.conf import settings

Employee = settings.AUTH_USER_MODEL


class QuestionCategory(models.Model):

    CATEGORY_CHOICES = [
        ("behavioral", "Behavioral"),
        ("performance", "Performance"),
    ]

    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=50, choices=CATEGORY_CHOICES)

    def __str__(self):
        return self.name


class QuestionParameter(models.Model):

    category = models.ForeignKey(
        QuestionCategory,
        on_delete=models.CASCADE,
        related_name="parameters"
    )

    question_text = models.TextField()

    department = models.CharField(
        max_length=150,
        null=True,
        blank=True
    )

    default_weightage = models.FloatField(default=1)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.question_text[:80]


class ReviewCycle(models.Model):

    name = models.CharField(max_length=100)

    start_date = models.DateField()
    end_date = models.DateField()

    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class EmployeeQuestionnaire(models.Model):
    STATUS_CHOICES = [
    ("draft", "Draft"),
    ("self_submitted", "Self Submitted"),
    ("under_rm_review", "Under RM Review"),
    ("rm_reviewed", "RM Reviewed"),
    ("under_skip_review", "Under Skip Review"),
    ("skip_reviewed", "Skip Reviewed"),
    ("under_peer_review", "Under Peer Review"),
    ("completed", "Completed"),
    ]

    employee = models.ForeignKey("employees.Employee", on_delete=models.CASCADE)
    review_cycle = models.ForeignKey("ReviewCycle", on_delete=models.CASCADE)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="draft")
    submitted_at = models.DateTimeField(null=True, blank=True)

    peer_reviewer = models.ForeignKey(
        "employees.Employee",
        null=True,
        blank=True,
        related_name="peer_reviews",
        on_delete=models.SET_NULL,
    )
    peer_requested_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

class EmployeeQuestionnaireItem(models.Model):
    employee_questionnaire = models.ForeignKey(
        EmployeeQuestionnaire,
        on_delete=models.CASCADE,
        related_name="items"
    )

    parameter = models.ForeignKey(
        QuestionParameter,
        on_delete=models.CASCADE
    )

    weightage = models.FloatField(default=1)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]
        unique_together = ("employee_questionnaire", "parameter")


class EmployeeQuestionnaireStageSubmission(models.Model):
    STAGE_CHOICES = [
        ("self", "Self"),
        ("rm", "Reporting Manager"),
        ("skip", "Skip Level Manager"),
        ("peer", "Peer"),
    ]

    employee_questionnaire = models.ForeignKey(
        "EmployeeQuestionnaire",
        on_delete=models.CASCADE
    )

    evaluator_type = models.CharField(
        max_length=20,
        choices=STAGE_CHOICES
    )

    submitted_by = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    feedback = models.TextField(blank=True, null=True)
    scope_of_improvement = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, default="draft")
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("employee_questionnaire", "evaluator_type")

class EmployeeQuestionnaireResponse(models.Model):

    REVIEWER_TYPE_CHOICES = [
        ("self", "Self"),
        ("rm", "Reporting Manager"),
        ("skip", "Skip Manager"),
        ("peer", "Peer"),
    ]

    submission = models.ForeignKey(
        "EmployeeQuestionnaireStageSubmission",
        on_delete=models.CASCADE
    )

    questionnaire_item = models.ForeignKey(
        "EmployeeQuestionnaireItem",
        on_delete=models.CASCADE
    )

    score = models.IntegerField()

    reviewer_type = models.CharField(
        max_length=20,
        choices=REVIEWER_TYPE_CHOICES,
        default="self"
    )