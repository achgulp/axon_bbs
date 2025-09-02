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


# Full path: axon_bbs/api/urls.py
from django.urls import path
from .views import (
    RegisterView,
    MessageBoardListView,
    MessageListView,
    PostMessageView,
    IgnorePubkeyView,
    BanPubkeyView,
    UnlockIdentityView,
    ImportIdentityView,
    UpdateNicknameView,
    UserProfileView,
    ExportIdentityView,
    UploadAvatarView,
    LogoutView,
    RequestContentExtensionView,
    ReviewContentExtensionView,
    UnpinContentView,
    SyncView,
    BitSyncHasContentView,
    BitSyncChunkView,
    FileUploadView,
    FileDownloadView,
    DownloadContentView,
    FileStatusView,
    GetPublicKeyView,
    SendPrivateMessageView,
    PrivateMessageListView,
    PrivateMessageOutboxView,
    AppletListView,
    GetSaveAppletDataView,
    HighScoreListView,
    PostAppletEventView,
    ReadAppletEventsView,
    # NEW: Views for the shared state reconciliation protocol
    AppletSharedStateView,
    AppletStateVersionView,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    # Auth
    path('register/', RegisterView.as_view(), name='register'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # Identity & User Profile
    path('identity/unlock/', UnlockIdentityView.as_view(), name='unlock-identity'),
    path('identity/import/', ImportIdentityView.as_view(), name='import-identity'),
    path('identity/export/', ExportIdentityView.as_view(), name='export-identity'),
    path('identity/public_key/', GetPublicKeyView.as_view(), name='get-public-key'),
    path('user/nickname/', UpdateNicknameView.as_view(), name='update-nickname'),
    path('user/profile/', UserProfileView.as_view(), name='user-profile'),
    path('user/avatar/', UploadAvatarView.as_view(), name='user-avatar'),

    # Private Messaging
    path('pm/send/', SendPrivateMessageView.as_view(), name='pm-send'),
    path('pm/list/', PrivateMessageListView.as_view(), name='pm-list'),
    path('pm/outbox/', PrivateMessageOutboxView.as_view(), name='pm-outbox'),

    # Content & Moderation
    path('boards/', MessageBoardListView.as_view(), name='board-list'),
    path('boards/<int:pk>/messages/', MessageListView.as_view(), name='message-list'),
    path('messages/post/', PostMessageView.as_view(), name='post-message'),
    path('user/ignore/', IgnorePubkeyView.as_view(), name='ignore-pubkey'),
    
    # Admin & Moderator Actions
    path('admin/ban/', BanPubkeyView.as_view(), name='ban-pubkey'),
    path('content/request-extension/', RequestContentExtensionView.as_view(), name='request-extension'),
    path('content/review-extension/<int:pk>/', ReviewContentExtensionView.as_view(), name='review-extension'),
    path('content/unpin/', UnpinContentView.as_view(), name='unpin-content'),

    # File & Content Handling
    path('files/upload/', FileUploadView.as_view(), name='file-upload'),
    path('files/download/<uuid:file_id>/', FileDownloadView.as_view(), name='file-download'),
    path('files/status/<uuid:file_id>/', FileStatusView.as_view(), name='file-status'),
    path('content/download/<str:content_hash>/', DownloadContentView.as_view(), name='content-download'),

    # Applet Framework
    path('applets/', AppletListView.as_view(), name='applet-list'),
    path('applets/<uuid:applet_id>/data/', GetSaveAppletDataView.as_view(), name='applet-data'),
    path('high_scores/<uuid:applet_id>/', HighScoreListView.as_view(), name='high-scores'),
    path('applets/<uuid:applet_id>/post_event/', PostAppletEventView.as_view(), name='applet-post-event'),
    path('applets/<uuid:applet_id>/read_events/', ReadAppletEventsView.as_view(), name='applet-read-events'),

    # NEW: Endpoints for applets to get shared world state
    path('applets/<uuid:applet_id>/shared_state/', AppletSharedStateView.as_view(), name='applet-shared-state'),
    path('applets/<uuid:applet_id>/state_version/', AppletStateVersionView.as_view(), name='applet-state-version'),

    # BitSync P2P Protocol
    path('sync/', SyncView.as_view(), name='sync'),
    path('bitsync/has_content/<str:content_hash>/', BitSyncHasContentView.as_view(), name='bitsync-has-content'),
    path('bitsync/chunk/<str:content_hash>/<int:chunk_index>/', BitSyncChunkView.as_view(), name='bitsync-chunk'),
]


