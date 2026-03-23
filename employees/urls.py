from django.urls import path
from .views import EmployeeListCreateView, EmployeeDetailView

urlpatterns = [
    path("", EmployeeListCreateView.as_view(), name="employee_list_create"),
    path("<int:pk>/", EmployeeDetailView.as_view(), name="employee_detail"),
]