from .dashboard_views import AdminDashboardView
from .question_views import (
    AdminQuestionCategoryListView,
    AdminQuestionListCreateView,
    AdminQuestionDetailView,
)
from .potential_question_views import (
    AdminPotentialQuestionListCreateView,
    AdminPotentialQuestionDetailView,
)
from .config_views import (
    AdminScoreConfigurationListCreateView,
    AdminScoreConfigurationDetailView,
    AdminScoreConfigurationActivateView,
    AdminPotentialConfigurationListCreateView,
    AdminPotentialConfigurationDetailView,
    AdminPotentialConfigurationActivateView,
    AdminAppraisalConfigurationListCreateView,
    AdminAppraisalConfigurationDetailView,
)
from .cycle_views import (
    AdminReviewCycleListCreateView,
    AdminReviewCycleDetailView,
    AdminReviewCycleActivateView,
)

from .reset_views import EmployeeResetPreviewView, EmployeeResetExecuteView, AdminReviewCycleListView