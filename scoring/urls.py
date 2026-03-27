from django.urls import path
from .views import (
    AdminScoringQuestionnaireListView,
    CalculateScoreView,
    ScoreResultView,
    HRScoreOverrideView,
    ReleaseScoreView,
    MyScoreView,
    CalculatePPIView,
    PPIResultView,
)

from .views_potential import (
    RMPotentialPendingView,
    SkipPotentialPendingView,
    RMPotentialFormView,
    SkipPotentialFormView,
    RMSavePotentialDraftView,
    SkipSavePotentialDraftView,
    RMSubmitPotentialView,
    SkipSubmitPotentialView,
    CalculatePotentialScoreView,
    PotentialResultView,
)

from .views_ninebox import (
    GenerateNineBoxPlacementView,
    NineBoxPlacementResultView,
)

from .views_appraisal import (
    GenerateAppraisalRecommendationView,
    AppraisalRecommendationResultView,
    AppraisalRecommendationOverrideView,
)

from .views_analytics_release import (
    AnalyticsReleaseStatusView,
    AnalyticsReleaseToggleView,
    MyAnalyticsReportView,
)

urlpatterns = [
    path(
        "admin/questionnaires/",
        AdminScoringQuestionnaireListView.as_view()
    ),
    path(
        "calculate/<int:questionnaire_id>/",
        CalculateScoreView.as_view()
    ),
    path(
        "result/<int:questionnaire_id>/",
        ScoreResultView.as_view()
    ),
    path(
        "override/<int:questionnaire_id>/",
        HRScoreOverrideView.as_view()
    ),
    path(
        "release/<int:questionnaire_id>/",
        ReleaseScoreView.as_view()
    ),
    path(
        "my-score/<int:questionnaire_id>/",
        MyScoreView.as_view()
    ),
    path(
        "ppi/calculate/<int:questionnaire_id>/",
        CalculatePPIView.as_view()
    ),
    path(
        "ppi/result/<int:questionnaire_id>/",
        PPIResultView.as_view()
    ),
    path("potential/rm/pending/", RMPotentialPendingView.as_view()),
    path("potential/skip/pending/", SkipPotentialPendingView.as_view()),

    path("potential/rm/form/<int:assessment_id>/", RMPotentialFormView.as_view()),
    path("potential/skip/form/<int:assessment_id>/", SkipPotentialFormView.as_view()),

    path("potential/rm/save/", RMSavePotentialDraftView.as_view()),
    path("potential/skip/save/", SkipSavePotentialDraftView.as_view()),

    path("potential/rm/submit/", RMSubmitPotentialView.as_view()),
    path("potential/skip/submit/", SkipSubmitPotentialView.as_view()),

    path("potential/calculate/<int:assessment_id>/", CalculatePotentialScoreView.as_view()),
    path("potential/result/<int:assessment_id>/", PotentialResultView.as_view()),

    path(
        "ninebox/generate/<int:questionnaire_id>/",
        GenerateNineBoxPlacementView.as_view()
    ),
    path(
        "ninebox/result/<int:questionnaire_id>/",
        NineBoxPlacementResultView.as_view()
    ),
        path(
        "appraisal/generate/<int:questionnaire_id>/",
        GenerateAppraisalRecommendationView.as_view()
    ),
    path(
        "appraisal/result/<int:questionnaire_id>/",
        AppraisalRecommendationResultView.as_view()
    ),
    path(
        "appraisal/override/<int:questionnaire_id>/",
        AppraisalRecommendationOverrideView.as_view()
    ),
    path(
    "analytics-release/<int:questionnaire_id>/",
    AnalyticsReleaseStatusView.as_view()
    ),
    path(
        "analytics-release/toggle/<int:questionnaire_id>/",
        AnalyticsReleaseToggleView.as_view()
    ),
    path("my-analytics/<int:questionnaire_id>/", MyAnalyticsReportView.as_view(), name="my_analytics_report"),
]