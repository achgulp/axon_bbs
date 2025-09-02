# Axon BBS - A modern, anonymous, federated bulletin board system.
# Copyright (C) 2025 Achduke7
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


# Full path: axon_bbs/axon_project/urls.py
"""
URL configuration for axon_project project.
"""
import os
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
# UPDATED: Added the missing import for static file serving
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.views.static import serve

class NoCacheTemplateView(TemplateView):
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    re_path(r'^(?P<path>manifest\.json)$', serve, {'document_root': os.path.join(settings.BASE_DIR, 'frontend/build')}),
    re_path(r'^(?P<path>favicon\.ico)$', serve, {'document_root': os.path.join(settings.BASE_DIR, 'frontend/build')}),
    re_path(r'^(?P<path>axon\.png)$', serve, {'document_root': os.path.join(settings.BASE_DIR, 'frontend/build')}),
    re_path(r'^.*', NoCacheTemplateView.as_view(template_name='index.html')),
]

# This block allows the development server to serve user-uploaded media files (like avatars)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
