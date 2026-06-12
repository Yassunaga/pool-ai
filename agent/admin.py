from django.contrib import admin

from .models import Agent, Lead


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'name', 'area_type', 'handoff_requested', 'handoff_notified', 'updated_at']
    list_filter = ['area_type', 'handoff_requested', 'handoff_notified']
    search_fields = ['session_id', 'name']
    readonly_fields = ['created_at', 'updated_at']
