from django.urls import path

from .views import (
    AdminDashboardView,
    AdminQuestionCategoryListView,
    AdminQuestionListCreateView,
    AdminQuestionDetailView,
    AdminPotentialQuestionListCreateView,
    AdminPotentialQuestionDetailView,
    AdminScoreConfigurationListCreateView,
    AdminScoreConfigurationDetailView,
    AdminScoreConfigurationActivateView,
    AdminPotentialConfigurationListCreateView,
    AdminPotentialConfigurationDetailView,
    AdminPotentialConfigurationActivateView,
    AdminAppraisalConfigurationListCreateView,
    AdminAppraisalConfigurationDetailView,
    AdminReviewCycleListCreateView,
    AdminReviewCycleDetailView,
    AdminReviewCycleActivateView,
    EmployeeResetPreviewView,
    EmployeeResetExecuteView,
    AdminReviewCycleListView,
)

urlpatterns = [
    path("dashboard/", AdminDashboardView.as_view(), name="admin_dashboard"),

    path("question-categories/", AdminQuestionCategoryListView.as_view(), name="admin_question_categories"),
    path("questions/", AdminQuestionListCreateView.as_view(), name="admin_questions"),
    path("questions/<int:question_id>/", AdminQuestionDetailView.as_view(), name="admin_question_detail"),

    path("potential-questions/", AdminPotentialQuestionListCreateView.as_view(), name="admin_potential_questions"),
    path("potential-questions/<int:question_id>/", AdminPotentialQuestionDetailView.as_view(), name="admin_potential_question_detail"),

    path("config/score/", AdminScoreConfigurationListCreateView.as_view(), name="admin_score_configurations"),
    path("config/score/<int:config_id>/", AdminScoreConfigurationDetailView.as_view(), name="admin_score_configuration_detail"),
    path("config/score/<int:config_id>/activate/", AdminScoreConfigurationActivateView.as_view(), name="admin_score_configuration_activate"),

    path("config/potential/", AdminPotentialConfigurationListCreateView.as_view(), name="admin_potential_configurations"),
    path("config/potential/<int:config_id>/", AdminPotentialConfigurationDetailView.as_view(), name="admin_potential_configuration_detail"),
    path("config/potential/<int:config_id>/activate/", AdminPotentialConfigurationActivateView.as_view(), name="admin_potential_configuration_activate"),

    path("config/appraisal/", AdminAppraisalConfigurationListCreateView.as_view(), name="admin_appraisal_configurations"),
    path("config/appraisal/<int:config_id>/", AdminAppraisalConfigurationDetailView.as_view(), name="admin_appraisal_configuration_detail"),

    path("cycles/", AdminReviewCycleListCreateView.as_view(), name="admin_review_cycles"),
    path("cycles/<int:cycle_id>/", AdminReviewCycleDetailView.as_view(), name="admin_review_cycle_detail"),
    path("cycles/<int:cycle_id>/activate/", AdminReviewCycleActivateView.as_view(), name="admin_review_cycle_activate"),
    path("reset/preview/", EmployeeResetPreviewView.as_view()),
    path("reset/execute/", EmployeeResetExecuteView.as_view()),
    path("cycles/list/", AdminReviewCycleListView.as_view()),

]