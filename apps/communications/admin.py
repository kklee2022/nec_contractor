from django.contrib import admin
from .models import Communication


@admin.register(Communication)
class CommunicationAdmin(admin.ModelAdmin):
    list_display = ['reference', 'project', 'communication_type', 'direction', 'sent_by', 'sent_date', 'acknowledged']
    list_filter = ['communication_type', 'direction', 'acknowledged', 'project']
    search_fields = ['reference', 'subject', 'body']
    readonly_fields = ['reference', 'created_at', 'updated_at']
