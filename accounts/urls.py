from django.urls import path
from .views import EmployeeLoginView, EmployeeMeView

urlpatterns = [
    path("login/", EmployeeLoginView.as_view(), name="employee_login"),
    path("me/", EmployeeMeView.as_view(), name="employee_me"),
]