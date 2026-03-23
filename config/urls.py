from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

def healthz(request):
    return HttpResponse("ok", content_type="text/plain")


urlpatterns = [
    path("healthz/", healthz),
    path("admin/", admin.site.urls),
    path("api/accounts/", include("accounts.urls")),
    path("api/employees/", include("employees.urls")),
    path("api/evaluations/", include("evaluations.urls")),
    path("api/scoring/", include("scoring.urls")),
    path("api/", include("healthcheck.urls")),
]