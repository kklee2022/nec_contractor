from django.contrib import admin
from .models import SubscriptionPlan, Organisation, OrganisationMembership


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'tier', 'price_monthly', 'max_projects', 'max_members', 'deadline_emails']
    list_editable = ['price_monthly', 'max_projects', 'max_members', 'deadline_emails']


class MembershipInline(admin.TabularInline):
    model = OrganisationMembership
    extra = 0
    fields = ['user', 'org_role', 'is_active']
    autocomplete_fields = ['user']


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'plan', 'status', 'active_member_count', 'project_count', 'created_at']
    list_filter = ['status', 'plan']
    search_fields = ['name', 'slug']
    inlines = [MembershipInline]
    readonly_fields = ['slug', 'created_at', 'updated_at']


@admin.register(OrganisationMembership)
class OrganisationMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'organisation', 'org_role', 'is_active', 'created_at']
    list_filter = ['org_role', 'is_active', 'organisation']
    search_fields = ['user__username', 'user__email', 'organisation__name']
    list_select_related = ['user', 'organisation']
