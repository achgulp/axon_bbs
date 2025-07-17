# axon_bbs/core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, MessageBoard, Message, FileArea, UploadedFile, PrivateMessage

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Use the correct field name 'access_level'
    list_display = ('username', 'email', 'access_level', 'is_staff')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('BBS Info', {'fields': ('access_level',)}),
    )

@admin.register(MessageBoard)
class MessageBoardAdmin(admin.ModelAdmin):
    # Use the correct field name 'required_access_level'
    list_display = ('name', 'description', 'required_access_level')
    list_filter = ('required_access_level',)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    # Use the correct field name 'subject' instead of 'title'
    list_display = ('subject', 'author', 'board', 'posted_at')
    list_filter = ('board', 'author')
    date_hierarchy = 'posted_at'

@admin.register(FileArea)
class FileAreaAdmin(admin.ModelAdmin):
    # Use the correct field names 'view_access_level' and 'upload_access_level'
    list_display = ('name', 'description', 'view_access_level', 'upload_access_level')

@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    # Use the correct field names 'file' and 'upload_date'
    list_display = ('file', 'uploader', 'area', 'upload_date')
    list_filter = ('area', 'uploader')
    date_hierarchy = 'upload_date'

@admin.register(PrivateMessage)
class PrivateMessageAdmin(admin.ModelAdmin):
    # Use the correct field names 'subject' and 'is_read'
    list_display = ('subject', 'sender', 'recipient', 'sent_at', 'is_read')
    list_filter = ('sender', 'recipient', 'is_read')
    date_hierarchy = 'sent_at'

