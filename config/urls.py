"""Main URL configuration for the NEC4 ECC Contractor Platform."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Auth (login / logout / password reset)
    path('accounts/', include('django.contrib.auth.urls')),

    # Redirect root → dashboard
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),

    # Core (dashboard, profile, people, register)
    path('', include('apps.core.urls')),

    # Projects
    path('projects/', include('apps.projects.urls')),

    # Early Warnings
    path('early-warnings/', include('apps.early_warnings.urls')),

    # Compensation Events
    path('compensation-events/', include('apps.compensation_events.urls')),

    # Communications
    path('communications/', include('apps.communications.urls')),

    # Financial
    path('financial/', include('apps.financial.urls')),

    # Subscriptions & Organisation management
    path('', include('apps.subscriptions.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

