from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def api_root(request):
    return JsonResponse({"service": "BusTick API", "admin": "/admin/", "health": "/api/health/", "routes": "/api/routes/"})


urlpatterns = [
    path("", api_root),
    path("admin/", admin.site.urls),
    path("api/", include("booking.urls")),
]
