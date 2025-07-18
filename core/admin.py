# axon_bbs/core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, MessageBoard, Message, PrivateMessage

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Use the correct field name 'access_level'
    list_display = ('username', 'email', 'access_level', 'is_staff', 'is_banned')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('BBS Info', {'fields': ('access_level', 'is_banned')}),
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'is_banned')

@admin.register(MessageBoard)
class MessageBoardAdmin(admin.ModelAdmin):
    # Use the correct field name 'required_access_level'
    list_display = ('name', 'description', 'required_access_level')
    list_filter = ('required_access_level',)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    # Use the correct field name 'subject' instead of 'title'
    list_display = ('subject', 'author', 'board', 'created_at', 'expires_at', 'is_pinned')
    list_filter = ('board', 'author', 'is_pinned')
    date_hierarchy = 'created_at'

@admin.register(PrivateMessage)
class PrivateMessageAdmin(admin.ModelAdmin):
    # Use the correct field names 'subject' and 'is_read'
    list_display = ('subject', 'author', 'recipient', 'created_at', 'is_read')
    list_filter = ('author', 'recipient', 'is_read')
    date_hierarchy = 'created_at'
