# Axon BBS - a modern, anonymous, federated bulletin board system.
# Copyright (C) 2025 Achduke7
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


# Full path: axon_bbs/applets/admin.py
from django import forms
from django.contrib import admin
from .models import Applet, AppletCategory, AppletData, AppletSharedState, HighScore
from core.models import FileAttachment

class AppletAdminForm(forms.ModelForm):
    code_source_file = forms.ModelChoiceField(
        queryset=FileAttachment.objects.all(),
        required=False,
        help_text="Select the applet's main JS file. The Code Manifest will be auto-populated from this on save.",
    )

    class Meta:
        model = Applet
        fields = '__all__'

@admin.register(Applet)
class AppletAdmin(admin.ModelAdmin):
    form = AppletAdminForm
    list_display = ('name', 'owner', 'category', 'is_local', 'created_at')
    list_filter = ('category', 'is_local', 'owner')
    search_fields = ('name', 'description', 'id', 'owner__username')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Core Information', {
            'fields': ('name', 'description', 'owner', 'category')
        }),
        ('Technical Details', {
            'fields': ('code_source_file', 'code_manifest', 'author_pubkey', 'parameters')
        }),
        ('Behavior', {
            'fields': ('is_local', 'is_debug_mode', 'handles_mime_types', 'event_board')
        }),
    )
    
    readonly_fields = ('id', 'created_at', 'author_pubkey', 'code_manifest')
    autocomplete_fields = ['owner']

    def save_model(self, request, obj, form, change):
        # Auto-populate the code_manifest from the selected source file.
        code_source_file = form.cleaned_data.get('code_source_file')
        if code_source_file and hasattr(code_source_file, 'metadata_manifest'):
            obj.code_manifest = code_source_file.metadata_manifest
        super().save_model(request, obj, form, change)

# Register other models from this app for admin management
admin.site.register(AppletCategory)
admin.site.register(AppletData)
admin.site.register(AppletSharedState)
admin.site.register(HighScore)
