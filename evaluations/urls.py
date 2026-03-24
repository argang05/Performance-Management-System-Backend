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
        # ===============================
    # SKIP LEVEL REVIEW
    # ===============================

    path(
        "skip/pending-reviews/",
        SkipPendingReviewsView.as_view(),
        name="skip_pending_reviews",
    ),

    path(
        "skip/review-form/<int:questionnaire_id>/",
        SkipReviewFormView.as_view(),
        name="skip_review_form",
    ),

    path(
        "skip/self-responses/<int:questionnaire_id>/",
        SkipSelfResponsesView.as_view(),
        name="skip_self_responses",
    ),

    path(
        "skip/rm-responses/<int:questionnaire_id>/",
        SkipRMResponsesView.as_view(),
        name="skip_rm_responses",
    ),

    path(
        "skip/save-draft/",
        SkipSaveDraftView.as_view(),
        name="skip_save_draft",
    ),

    path(
        "skip/submit/",
        SkipSubmitReviewView.as_view(),
        name="skip_submit_review",
    ),

    path("peer/search/", PeerEmployeeSearchView.as_view()),
    path("peer/recommend/", PeerRecommendView.as_view()),
    path("peer/pending-reviews/", PeerPendingReviewsView.as_view()),
    path("peer/review-form/<int:questionnaire_id>/", PeerReviewFormView.as_view()),
    path("peer/save-draft/", PeerSaveDraftView.as_view()),
    path("peer/submit/", PeerSubmitReviewView.as_view()),
    path("peer/self-responses/<int:questionnaire_id>/", PeerSelfResponsesView.as_view()),
]

urlpatterns += [
    path(
        "admin/delete-questionnaire/<int:questionnaire_id>/",
        DeleteEmployeeQuestionnaireView.as_view(),
        name="delete_questionnaire",
    ),
]