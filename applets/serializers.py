# Full path: axon_bbs/applets/serializers.py
from rest_framework import serializers
from .models import Applet, HighScore
from core.models import User

class AppletSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)
    class Meta:
        model = Applet
        fields = ('id', 'name', 'description', 'author_pubkey', 'code_manifest', 'created_at', 'category_name', 'is_debug_mode', 'handles_mime_types')
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
