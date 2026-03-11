from django.contrib import admin
from .models import CompensationEvent, CEAttachment


class CEAttachmentInline(admin.TabularInline):
    model = CEAttachment
    extra = 0


@admin.register(CompensationEvent)
class CompensationEventAdmin(admin.ModelAdmin):
    list_display = ['reference', 'project', 'clause', 'state', 'notification_date',
                    'pm_reply_overdue', 'quotation_cost']
    list_filter = ['state', 'clause', 'project']
    search_fields = ['reference', 'description', 'project__name']
    readonly_fields = ['reference', 'state', 'created_at', 'updated_at',
                       'pm_reply_deadline', 'pm_reply_overdue']
    inlines = [CEAttachmentInline]
