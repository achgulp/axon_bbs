# axon_bbs/api/urls.py
from django.urls import path
from .views import (
    RegisterView,
    MessageBoardListView,
    PostNostrMessageView,
    IgnoreUserView,
    BanUserView,
    UnlockIdentityView,
    LogoutView
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

    # Content & Moderation
    path('boards/', MessageBoardListView.as_view(), name='board-list'),
    path('messages/post/', PostNostrMessageView.as_view(), name='post-message'),
    path('user/ignore/', IgnoreUserView.as_view(), name='ignore-user'),
    path('admin/ban/', BanUserView.as_view(), name='ban-user'),
]
