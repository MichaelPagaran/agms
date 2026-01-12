"""
URL configuration for AGMS project.
"""
from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI

api = NinjaAPI(
    title="AGMS API",
    version="1.0.0",
    description="Association Governance Management System API",
    docs_url="/docs",
)

# Register app routers here as they are built
from apps.identity.api import router as identity_router
api.add_router("/identity/", identity_router)
# from apps.organizations.api import ...

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]
