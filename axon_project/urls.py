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

# Import views from each app with a namespace
from accounts import views as accounts_views
from messaging import views as messaging_views
from federation import views as federation_views
from applets import views as applets_views


class NoCacheTemplateView(TemplateView):
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

api_urlpatterns = [
    # Core URLs (includes SSE endpoint for chat)
    path('', include('core.urls')),

    # Auth & Config
    path('register/', accounts_views.RegisterView.as_view(), name='register'),
    path('token/', accounts_views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', accounts_views.LogoutView.as_view(), name='logout'),
    path('config/timezone/', accounts_views.GetDisplayTimezoneView.as_view(), name='get-timezone'),
    
    # Identity & User Profile
    path('identity/import/', accounts_views.ImportIdentityView.as_view(), name='import-identity'),
    path('identity/export/', accounts_views.ExportIdentityView.as_view(), name='export-identity'),
    path('identity/public_key/', accounts_views.GetPublicKeyView.as_view(), name='get-public-key'),
    path('identity/claim/', accounts_views.ClaimAccountView.as_view(), name='claim-identity'),
    
    path('user/profile/', accounts_views.UserProfileView.as_view(), name='user-profile'),
    path('user/nickname/', accounts_views.UpdateNicknameView.as_view(), name='update-nickname'),
    path('user/avatar/', accounts_views.UploadAvatarView.as_view(), name='user-avatar'),
    path('user/timezone/', accounts_views.UpdateTimezoneView.as_view(), name='update-timezone'),
    path('user/change_password/', accounts_views.ChangePasswordView.as_view(), name='change-password'),
    path('user/reset_security_questions/', accounts_views.ResetSecurityQuestionsView.as_view(), name='reset-security-questions'),

    # Recovery URLs
    path('recovery/get_questions/', accounts_views.GetSecurityQuestionsView.as_view(), name='recovery-get-questions'),
    path('recovery/submit/', accounts_views.SubmitRecoveryView.as_view(), name='recovery-submit'),
    
    # Private Messaging
    path('pm/send/', messaging_views.SendPrivateMessageView.as_view(), name='pm-send'),
    path('pm/list/', messaging_views.PrivateMessageListView.as_view(), name='pm-list'),
    path('pm/outbox/', messaging_views.PrivateMessageOutboxView.as_view(), name='pm-outbox'),
    path('pm/delete/<uuid:pk>/', messaging_views.DeletePrivateMessageView.as_view(), name='pm-delete'),

    # Content & Moderation
    path('boards/', messaging_views.MessageBoardListView.as_view(), name='board-list'),
    path('boards/<int:pk>/messages/', messaging_views.MessageListView.as_view(), name='message-list'),
    path('messages/post/', messaging_views.PostMessageView.as_view(), name='post-message'),
    path('files/upload/', messaging_views.FileUploadView.as_view(), name='file-upload'),
    path('user/ignore/', federation_views.IgnorePubkeyView.as_view(), name='ignore-pubkey'),
    path('messages/report/', federation_views.ReportMessageView.as_view(), name='report-message'),
    path('moderation/contact/', federation_views.ContactModeratorsView.as_view(), name='moderation-contact'),
    path('moderation/unified_queue/', federation_views.UnifiedQueueView.as_view(), name='moderation-unified-queue'),
    path('moderation/review/<int:report_id>/', federation_views.ReviewReportView.as_view(), name='mod-review'),
    path('moderation/profile_review/<uuid:action_id>/', federation_views.ReviewProfileUpdateView.as_view(), name='mod-profile-review'),
    
    # Admin & Moderator Actions
    path('admin/ban/', federation_views.BanPubkeyView.as_view(), name='ban-pubkey'),
    path('content/request-extension/', federation_views.RequestContentExtensionView.as_view(), name='request-extension'),
    path('content/review-extension/<int:pk>/', federation_views.ReviewContentExtensionView.as_view(), name='review-extension'),
    path('content/unpin/', federation_views.UnpinContentView.as_view(), name='unpin-content'),
    path('content/download/<str:content_hash>/', messaging_views.DownloadContentView.as_view(), name='content-download'),
    path('content/stream/<str:content_hash>/', messaging_views.StreamContentView.as_view(), name='content-stream'),

    # Applet Framework
    path('applets/', applets_views.AppletListView.as_view(), name='applet-list'),
    path('applets/<uuid:applet_id>/data/', applets_views.GetSaveAppletDataView.as_view(), name='applet-data'),
    path('high_scores/<uuid:applet_id>/', applets_views.HighScoreListView.as_view(), name='high-scores'),
    path('applets/<uuid:applet_id>/post_event/', applets_views.PostAppletEventView.as_view(), name='applet-post-event'),
    path('applets/<uuid:applet_id>/read_events/', applets_views.ReadAppletEventsView.as_view(), name='applet-read-events'),
    path('applets/<uuid:applet_id>/shared_state/', applets_views.AppletSharedStateView.as_view(), name='applet-shared-state'),
    path('applets/<uuid:applet_id>/state_version/', applets_views.AppletStateVersionView.as_view(), name='applet-state-version'),
    path('applets/<uuid:applet_id>/update_state/', applets_views.UpdateStateView.as_view(), name='applet-update-state'),
    path('chat/post/', applets_views.PostChatMessageView.as_view(), name='post-chat-message'),
    path('libraries/<str:library_name>/', messaging_views.StreamLibraryView.as_view(), name='stream-library'),

    # Room-based endpoints for federation (rooms can span multiple applet instances)
    path('rooms/<str:room_id>/shared_state/', applets_views.RoomSharedStateView.as_view(), name='room-shared-state'),

    # BitSync P2P Protocol
    path('sync/', federation_views.SyncView.as_view(), name='sync'),
    path('bitsync/has_content/<str:content_hash>/', federation_views.BitSyncHasContentView.as_view(), name='bitsync-has-content'),
    path('bitsync/chunk/<str:content_hash>/<int:chunk_index>/', federation_views.BitSyncChunkView.as_view(), name='bitsync-chunk'),

    # Federation Admin
    path('federation/export_config/', federation_views.ExportConfigView.as_view(), name='federation-export-config'),
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
