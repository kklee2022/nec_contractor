from django.contrib import admin
from .models import Project, Site, Programme


class SiteInline(admin.TabularInline):
    model = Site
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['reference', 'name', 'status', 'contractor', 'project_manager', 'start_date', 'completion_date']
    list_filter = ['status']
    search_fields = ['name', 'reference']
    inlines = [SiteInline]
    filter_horizontal = ['members']


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ['project', 'revision', 'status', 'submitted_by', 'submitted_date']
    list_filter = ['status']
