from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include('accounts.urls')),
    path('api/employees/', include('employees.urls')),
    path('api/evaluations/', include('evaluations.urls')),
    path('api/scoring/', include('scoring.urls')),
    path("api/", include("healthcheck.urls")),
]