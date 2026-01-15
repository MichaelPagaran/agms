"""
URL configuration for AGMS project.
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
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
from apps.ledger.api import router as ledger_router
from apps.assets.api import router as assets_router

api.add_router("/identity/", identity_router)
api.add_router("/registry/units/", registry_router)
api.add_router("/organizations/", organizations_router)
api.add_router("/ledger/", ledger_router)
api.add_router("/assets/", assets_router)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(
        getattr(settings, 'MEDIA_URL', '/media/'),
        document_root=getattr(settings, 'MEDIA_ROOT', settings.BASE_DIR / 'media')
    )
