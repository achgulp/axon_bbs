# axon_bbs/axon_project/urls.py
"""
URL configuration for axon_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
# --- Import settings and static for media files ---
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Route for the Django admin interface
    path('admin/', admin.site.urls),
    
    # Route for our application's API
    path('api/', include('api.urls')),
]

# --- Add this block to serve media files in development ---
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

