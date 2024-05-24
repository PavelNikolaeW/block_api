from django.contrib import admin
from .models import Block
from django import forms


class BlockAdminForm(forms.ModelForm):
    class Meta:
        model = Block
        fields = '__all__'


class BlockAdmin(admin.ModelAdmin):
    list_display = ('id', 'creator', 'text', 'created_at', 'get_editable_users')
    search_fields = ('text', 'creator__username')
    list_filter = ('created_at', 'creator')
    date_hierarchy = 'created_at'
    form = BlockAdminForm
    filter_horizontal = ('visible_to_users', 'editable_by_users', 'children')

    def get_editable_users(self, obj):
        return ", ".join([user.username for user in obj.editable_by_users.all()])
    get_editable_users.short_description = 'Editable Users'  # Название столбца в админке


admin.site.register(Block, BlockAdmin)
