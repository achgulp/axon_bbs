# Axon BBS - A modern, anonymous, federated bulletin board system.
# Copyright (C) 2025 Achduke7
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY;
# without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.
# If not, see <https://www.gnu.org/licenses/>.


# Full path: axon_bbs/api/views/__init__.py
# This file makes the 'views' directory a Python package and exposes
# all the view classes from their separate modules, so they can still
# be imported from 'api.views'.
from .auth_views import (
    RegisterView,
    LogoutView,
    UnlockIdentityView,
    ImportIdentityView,
    ExportIdentityView,
    UpdateNicknameView,
    UserProfileView,
    UploadAvatarView,
    GetPublicKeyView,
    GetSecurityQuestionsView,
    SubmitRecoveryView,
    ClaimAccountView,
    ChangePasswordView,
    ResetSecurityQuestionsView,
    GetDisplayTimezoneView,
    UpdateTimezoneView,
)

from .content_views import (
    MessageBoardListView,
    MessageListView,
    PostMessageView,
    PrivateMessageListView,
    PrivateMessageOutboxView,
    SendPrivateMessageView,
    DeletePrivateMessageView, # <-- ADD THIS LINE
)

from .moderation_views import (
    IgnorePubkeyView,
    BanPubkeyView,
    ReportMessageView,
    ModeratorQueueView,
    ReviewReportView,
    RequestContentExtensionView,
    ReviewContentExtensionView,
    UnpinContentView,
    PendingProfileUpdatesQueueView,
    ReviewProfileUpdateView,
    # --- MODIFICATION START ---
    # The ServeTemporaryAvatarView is no longer needed with the new workflow.
    # --- MODIFICATION END ---
)

from .applet_views import (
    AppletListView,
    GetSaveAppletDataView,
    HighScoreListView,
    PostAppletEventView,
    ReadAppletEventsView,
    AppletSharedStateView,
    AppletStateVersionView,
)

from .federation_views import (
    SyncView,
    BitSyncHasContentView,
    BitSyncChunkView,
)
