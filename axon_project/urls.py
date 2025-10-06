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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.


# Full path: axon_bbs/axon_project/urls.py
"""
URL configuration for axon_project project.
"""
import os
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.views.static import serve

from rest_framework_simplejwt.views import TokenRefreshView
from accounts.views import (
    CustomTokenObtainPairView, 
    RegisterView, LogoutView, ImportIdentityView,
    ExportIdentityView, UpdateNicknameView, UserProfileView, UploadAvatarView,
    GetPublicKeyView, GetSecurityQuestionsView, SubmitRecoveryView, ClaimAccountView,
    ChangePasswordView, ResetSecurityQuestionsView, GetDisplayTimezoneView, UpdateTimezoneView
)
from messaging.views import (
    MessageBoardListView, MessageListView, PostMessageView, PrivateMessageListView,
    PrivateMessageOutboxView, SendPrivateMessageView, DeletePrivateMessageView,
    DownloadContentView, StreamContentView, FileUploadView, StreamLibraryView
)
from federation.views import (
    SyncView, BitSyncHasContentView, BitSyncChunkView, IgnorePubkeyView, BanPubkeyView,
    ReportMessageView, ReviewReportView, RequestContentExtensionView,
    ReviewContentExtensionView, UnpinContentView, ReviewProfileUpdateView,
    UnifiedQueueView, ContactModeratorsView, ExportConfigView
)
from applets.views import (
    AppletListView, GetSaveAppletDataView, HighScoreListView, PostAppletEventView,
    ReadAppletEventsView, AppletSharedStateView, AppletStateVersionView, UpdateStateView
)


class NoCacheTemplateView(TemplateView):
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

api_urlpatterns = [
    # Auth & Config
    path('register/', RegisterView.as_view(), name='register'),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('config/timezone/', GetDisplayTimezoneView.as_view(), name='get-timezone'),
    
    # Identity & User Profile
    path('identity/import/', ImportIdentityView.as_view(), name='import-identity'),
    path('identity/export/', ExportIdentityView.as_view(), name='export-identity'),
    path('identity/public_key/', GetPublicKeyView.as_view(), name='get-public-key'),
    path('identity/claim/', ClaimAccountView.as_view(), name='claim-identity'),
    
    path('user/profile/', UserProfileView.as_view(), name='user-profile'),
    path('user/nickname/', UpdateNicknameView.as_view(), name='update-nickname'),
    path('user/avatar/', UploadAvatarView.as_view(), name='user-avatar'),
    path('user/timezone/', UpdateTimezoneView.as_view(), name='update-timezone'),
    path('user/change_password/', ChangePasswordView.as_view(), name='change-password'),
    path('user/reset_security_questions/', ResetSecurityQuestionsView.as_view(), name='reset-security-questions'),

    # Recovery URLs
    path('recovery/get_questions/', GetSecurityQuestionsView.as_view(), name='recovery-get-questions'),
    path('recovery/submit/', SubmitRecoveryView.as_view(), name='recovery-submit'),
    
    # Private Messaging
    path('pm/send/', SendPrivateMessageView.as_view(), name='pm-send'),
    path('pm/list/', PrivateMessageListView.as_view(), name='pm-list'),
    path('pm/outbox/', PrivateMessageOutboxView.as_view(), name='pm-outbox'),
    path('pm/delete/<uuid:pk>/', DeletePrivateMessageView.as_view(), name='pm-delete'),

    # Content & Moderation
    path('boards/', MessageBoardListView.as_view(), name='board-list'),
    path('boards/<int:pk>/messages/', MessageListView.as_view(), name='message-list'),
    path('messages/post/', PostMessageView.as_view(), name='post-message'),
    path('files/upload/', FileUploadView.as_view(), name='file-upload'),
    path('user/ignore/', IgnorePubkeyView.as_view(), name='ignore-pubkey'),
    path('messages/report/', ReportMessageView.as_view(), name='report-message'),
    path('moderation/contact/', ContactModeratorsView.as_view(), name='moderation-contact'),
    path('moderation/unified_queue/', UnifiedQueueView.as_view(), name='moderation-unified-queue'),
    path('moderation/review/<int:report_id>/', ReviewReportView.as_view(), name='mod-review'),
    path('moderation/profile_review/<uuid:action_id>/', ReviewProfileUpdateView.as_view(), name='mod-profile-review'),
    
    # Admin & Moderator Actions
    path('admin/ban/', BanPubkeyView.as_view(), name='ban-pubkey'),
    path('content/request-extension/', RequestContentExtensionView.as_view(), name='request-extension'),
    path('content/review-extension/<int:pk>/', ReviewContentExtensionView.as_view(), name='review-extension'),
    path('content/unpin/', UnpinContentView.as_view(), name='unpin-content'),
    path('content/download/<str:content_hash>/', DownloadContentView.as_view(), name='content-download'),
    path('content/stream/<str:content_hash>/', StreamContentView.as_view(), name='content-stream'),

    # Applet Framework
    path('applets/', AppletListView.as_view(), name='applet-list'),
    path('applets/<uuid:applet_id>/data/', GetSaveAppletDataView.as_view(), name='applet-data'),
    path('high_scores/<uuid:applet_id>/', HighScoreListView.as_view(), name='high-scores'),
    path('applets/<uuid:applet_id>/post_event/', PostAppletEventView.as_view(), name='applet-post-event'),
    path('applets/<uuid:applet_id>/read_events/', ReadAppletEventsView.as_view(), name='applet-read-events'),
    path('applets/<uuid:applet_id>/shared_state/', AppletSharedStateView.as_view(), name='applet-shared-state'),
    path('applets/<uuid:applet_id>/state_version/', AppletStateVersionView.as_view(), name='applet-state-version'),
    path('applets/<uuid:applet_id>/update_state/', UpdateStateView.as_view(), name='applet-update-state'),
    path('libraries/<str:library_name>/', StreamLibraryView.as_view(), name='stream-library'),

    # BitSync P2P Protocol
    path('sync/', SyncView.as_view(), name='sync'),
    path('bitsync/has_content/<str:content_hash>/', BitSyncHasContentView.as_view(), name='bitsync-has-content'),
    path('bitsync/chunk/<str:content_hash>/<int:chunk_index>/', BitSyncChunkView.as_view(), name='bitsync-chunk'),

    # Federation Admin
    path('federation/export_config/', ExportConfigView.as_view(), name='federation-export-config'),
]


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(api_urlpatterns)),
    re_path(r'^(?P<path>manifest\.json)$', serve, {'document_root': os.path.join(settings.BASE_DIR, 'frontend/build')}),
    re_path(r'^(?P<path>favicon\.ico)$', serve, {'document_root': os.path.join(settings.BASE_DIR, 'frontend/build')}),
    re_path(r'^(?P<path>axon\.png)$', serve, {'document_root': os.path.join(settings.BASE_DIR, 'frontend/build')}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
    re_path(r'^.*', NoCacheTemplateView.as_view(template_name='index.html')),
]
