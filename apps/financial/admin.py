from django.contrib import admin
from .models import DefinedCost, PaymentApplication


@admin.register(DefinedCost)
class DefinedCostAdmin(admin.ModelAdmin):
    list_display = ['project', 'category', 'description', 'amount', 'currency', 'cost_date']
    list_filter = ['category', 'project', 'currency']
    search_fields = ['description', 'project__name']


@admin.register(PaymentApplication)
class PaymentApplicationAdmin(admin.ModelAdmin):
    list_display = ['project', 'application_number', 'status', 'gross_amount',
                    'net_amount', 'submitted_date', 'is_overdue']
    list_filter = ['status', 'project']
    readonly_fields = ['is_overdue']
