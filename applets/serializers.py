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


# Full path: axon_bbs/applets/serializers.py
from rest_framework import serializers
from .models import Applet, HighScore
from core.models import User

class AppletSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)
    class Meta:
        model = Applet
        fields = ('id', 'name', 'description', 'author_pubkey', 'code_manifest', 'created_at', 'category_name', 'is_debug_mode', 'handles_mime_types', 'parameters')
        read_only_fields = fields

class HighScoreSerializer(serializers.ModelSerializer):
    owner_avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = HighScore
        fields = ('owner_nickname', 'owner_avatar_url', 'score', 'wins', 'losses', 'kills', 'deaths', 'assists', 'last_updated')

    def get_owner_avatar_url(self, obj):
        user = User.objects.filter(pubkey=obj.owner_pubkey).first()
        if user and user.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(user.avatar.url)
            return user.avatar.url
        return None
