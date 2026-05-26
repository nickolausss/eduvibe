from django.contrib import admin
from .models import Scenario


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ['title', 'session_key', 'direction', 'grade', 'format_type', 'created_at']
    list_filter = ['direction', 'grade', 'format_type', 'created_at']
    search_fields = ['title', 'theme', 'session_key']
    readonly_fields = ['created_at', 'updated_at']