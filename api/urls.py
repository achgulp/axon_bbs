# Full path: axon_bbs/api/urls.py
from django.urls import path
from .views import (
    # Auth & Identity
    RegisterView,
    LogoutView,
    UnlockIdentityView,
    ImportIdentityView,
    
    # Content & Moderation
    MessageBoardListView,
    MessageListView,
    PostMessageView,
    IgnorePubkeyView,
    BanPubkeyView,
    RequestContentExtensionView,
    ReviewContentExtensionView,
    UnpinContentView,

    # File Handling
    FileUploadView,
    FileDownloadView, # NEW

    # BitSync P2P Protocol Endpoints
    SyncView,
    BitSyncHasContentView,
    BitSyncChunkView,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    # --- Auth & Identity ---
    path('register/', RegisterView.as_view(), name='register'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('identity/unlock/', UnlockIdentityView.as_view(), name='unlock-identity'),
    path('identity/import/', ImportIdentityView.as_view(), name='import-identity'),

    # --- Content & Moderation ---
    path('boards/', MessageBoardListView.as_view(), name='board-list'),
    path('boards/<int:pk>/messages/', MessageListView.as_view(), name='message-list'),
    path('messages/post/', PostMessageView.as_view(), name='post-message'),
    path('user/ignore/', IgnorePubkeyView.as_view(), name='ignore-pubkey'),
    path('admin/ban/', BanPubkeyView.as_view(), name='ban-pubkey'),
    path('content/request-extension/', RequestContentExtensionView.as_view(), name='request-extension'),
    path('content/review-extension/<int:pk>/', ReviewContentExtensionView.as_view(), name='review-extension'),
    path('content/unpin/', UnpinContentView.as_view(), name='unpin-content'),

    # --- File Handling ---
    path('files/upload/', FileUploadView.as_view(), name='file-upload'),
    # NEW: Endpoint to download a processed file
    path('files/download/<uuid:file_id>/', FileDownloadView.as_view(), name='file-download'),

    # --- BitSync P2P Protocol ---
    path('sync/', SyncView.as_view(), name='sync'),
    path('bitsync/has_content/<str:content_hash>/', BitSyncHasContentView.as_view(), name='bitsync-has-content'),
    path('bitsync/chunk/<str:content_hash>/<int:chunk_index>/', BitSyncChunkView.as_view(), name='bitsync-chunk'),
]

