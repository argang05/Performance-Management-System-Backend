from evaluations.models import EmployeeQuestionnaire

updated = EmployeeQuestionnaire.objects.filter(
    status="self_submitted"
).update(status="under_rm_review")

print(f"Updated {updated} questionnaires to under_rm_review")