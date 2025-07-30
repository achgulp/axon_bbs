# Full path: axon_bbs/axon_project/urls.py
"""
URL configuration for axon_project project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

# ✅ NEW: A custom view to force browsers not to cache the main app page.
class NoCacheTemplateView(TemplateView):
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

urlpatterns = [
    # Route for the Django admin interface
    path('admin/', admin.site.urls),
    
    # CORRECT ORDER: Route for the API must come BEFORE the catch-all
    path('api/', include('api.urls')),
    
    # Catch-all route to serve the React app's index.html
    # using our new no-cache view.
    re_path(r'^.*', NoCacheTemplateView.as_view(template_name='index.html')),
]

# This block to serve media files in development remains the same
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
