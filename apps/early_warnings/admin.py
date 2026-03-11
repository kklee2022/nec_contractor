from django.contrib import admin
from auditlog.models import LogEntry
from .models import EarlyWarning, EarlyWarningAttachment


class AttachmentInline(admin.TabularInline):
    model = EarlyWarningAttachment
    extra = 0


@admin.register(EarlyWarning)
class EarlyWarningAdmin(admin.ModelAdmin):
    list_display = ['reference', 'project', 'raised_by_party', 'status', 'created_at']
    list_filter = ['status', 'raised_by_party', 'project']
    search_fields = ['reference', 'description', 'project__name']
    inlines = [AttachmentInline]
    readonly_fields = ['reference', 'created_at', 'updated_at']
