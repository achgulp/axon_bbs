# axon_bbs/api/urls.py
from django.urls import path
from .views import (
    RegisterView,
    MessageBoardListView,
    PostNostrMessageView
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('boards/', MessageBoardListView.as_view(), name='board-list'),
    path('messages/post/', PostNostrMessageView.as_view(), name='post-message'),
]

