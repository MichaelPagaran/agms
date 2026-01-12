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

from apps.identity.api import router as identity_router
from apps.registry.api import router as registry_router
from apps.organizations.api import router as organizations_router

api.add_router("/identity/", identity_router)
api.add_router("/registry/units/", registry_router)
api.add_router("/organizations/", organizations_router)
# from apps.organizations.api import ...

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]
