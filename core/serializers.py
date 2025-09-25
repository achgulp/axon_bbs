# Full path: axon_bbs/core/serializers.py
from rest_framework import serializers
from .models import FileAttachment

class FileAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileAttachment
        fields = ('id', 'filename', 'content_type', 'size', 'created_at', 'metadata_manifest')
        read_only_fields = fields
