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
    LogoutView,
    ReceiveMagnetView,
    RequestContentExtensionView,
    ReviewContentExtensionView,
    UnpinContentView,
    TorrentFileView,
    SyncView,
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
    
    # Identity
    path('identity/unlock/', UnlockIdentityView.as_view(), name='unlock-identity'),
    path('identity/import/', ImportIdentityView.as_view(), name='import-identity'),

    # Content & Moderation
    path('boards/', MessageBoardListView.as_view(), name='board-list'),
    path('boards/<int:pk>/messages/', MessageListView.as_view(), name='message-list'),
    path('messages/post/', PostMessageView.as_view(), name='post-message'),
    path('receive_magnet/', ReceiveMagnetView.as_view(), name='receive-magnet'),
    path('user/ignore/', IgnorePubkeyView.as_view(), name='ignore-pubkey'),
    
    # Admin & Moderator Actions
    path('admin/ban/', BanPubkeyView.as_view(), name='ban-pubkey'),
    path('content/request-extension/', RequestContentExtensionView.as_view(), name='request-extension'),
    path('content/review-extension/<int:pk>/', ReviewContentExtensionView.as_view(), name='review-extension'),
    path('content/unpin/', UnpinContentView.as_view(), name='unpin-content'),

    # Endpoint for serving torrent files for web seeding
    path('torrents/<str:info_hash>/', TorrentFileView.as_view(), name='torrent-file'),

    # Endpoint for peers to poll for new messages
    path('sync/', SyncView.as_view(), name='sync'),
]
