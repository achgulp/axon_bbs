# axon_bbs/axon_project/urls.py
"""
URL configuration for axon_project project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
# --- Import settings and static for media files ---
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    # Route for the Django admin interface
    path('admin/', admin.site.urls),
    
    # Route for our application's API
    path('api/', include('api.urls')),
    
    # Add this: A catch-all route to serve the React app's index.html
    # for any route not handled by the above.
    re_path(r'^.*', TemplateView.as_view(template_name='index.html')),
]

# This block to serve media files in development remains the same
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
