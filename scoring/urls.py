from django.urls import path
from .views import CalculateScoreView, ScoreResultView, AdminScoringQuestionnaireListView

urlpatterns = [

    path(
        "calculate/<int:questionnaire_id>/",
        CalculateScoreView.as_view()
    ),

    path(
        "result/<int:questionnaire_id>/",
        ScoreResultView.as_view()
    ),
    path(
        "admin/questionnaires/",
        AdminScoringQuestionnaireListView.as_view()
    ),
]