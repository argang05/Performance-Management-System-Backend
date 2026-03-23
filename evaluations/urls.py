from django.urls import path
from .views import *

urlpatterns = [

    path(
        "self-questionnaire/",
        SelfQuestionnaireView.as_view()
    ),

    path(
        "self-questionnaire/save/",
        SaveSelfEvaluation.as_view()
    ),

    path(
        "self-questionnaire/submit/",
        SubmitSelfEvaluation.as_view()
    ),

    path(
    "self-review-status/",
        SelfReviewStatusView.as_view()
    ),

    path(
    "recommend-peer/",
        RecommendPeerView.as_view()
    ),

    path(
    "rm/pending-reviews/",
        ReportingManagerQueueView.as_view()
    ),

    path(
    "rm/review-form/<int:questionnaire_id>/",
    RMReviewFormView.as_view()
),

    path(
        "rm/self-responses/<int:questionnaire_id>/",
        RMViewSelfResponses.as_view()
    ),

    path(
        "rm/save-draft/",
        RMSaveDraftView.as_view()
    ),

    path(
        "rm/submit/",
        RMSubmitReviewView.as_view()
    ),
]

urlpatterns += [
    path(
        "admin/delete-questionnaire/<int:questionnaire_id>/",
        DeleteEmployeeQuestionnaireView.as_view(),
        name="delete_questionnaire",
    ),
]