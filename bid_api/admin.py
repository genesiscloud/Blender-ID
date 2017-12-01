from django.contrib import admin
from django.contrib.admin import ModelAdmin

from . import models

from bid_main.admin_decorators import short_description


@short_description('Disable selected webhooks')
def disable_webhook(modeladmin, request, queryset):
    queryset.update(enabled=False)


@short_description('Enable selected webhooks')
def enable_webhook(modeladmin, request, queryset):
    queryset.update(enabled=True)


@admin.register(models.Webhook)
class WebhookAdmin(ModelAdmin):
    list_display = ('name', 'hook_type', 'url', 'enabled')
    list_display_links = ('name', 'hook_type', 'url')
    list_filter = ('hook_type', 'enabled')
    search_fields = ('name', 'hook_type', 'url')
    ordering = ('name',)
    actions = [disable_webhook, enable_webhook]
