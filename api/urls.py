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
    FileStatusView,
    GetPublicKeyView,
    SendPrivateMessageView,
    PrivateMessageListView,
    PrivateMessageOutboxView,
    AppletListView,
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

    # File Handling
    path('files/upload/', FileUploadView.as_view(), name='file-upload'),
    path('files/download/<uuid:file_id>/', FileDownloadView.as_view(), name='file-download'),
    path('files/status/<uuid:file_id>/', FileStatusView.as_view(), name='file-status'),

    # Applet Framework
    path('applets/', AppletListView.as_view(), name='applet-list'),

    # BitSync P2P Protocol
    path('sync/', SyncView.as_view(), name='sync'),
    path('bitsync/has_content/<str:content_hash>/', BitSyncHasContentView.as_view(), name='bitsync-has-content'),
    path('bitsync/chunk/<str:content_hash>/<int:chunk_index>/', BitSyncChunkView.as_view(), name='bitsync-chunk'),
]
