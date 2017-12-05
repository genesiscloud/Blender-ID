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
    list_display = ('name', 'hook_type', 'url', 'enabled', 'queue_size')
    list_display_links = ('name', 'hook_type', 'url')
    list_filter = ('hook_type', 'enabled')
    search_fields = ('name', 'hook_type', 'url')
    ordering = ('name',)
    actions = [disable_webhook, enable_webhook]

    def queue_size(self, item: models.Webhook) -> str:
        """The queue size of the webhook, or '-' when empty."""
        return str(item.queue_size() or '-')


@short_description('Flush entire queue now')
def flush_queue_now(modeladmin, request, queryset):
    models.WebhookQueuedCall.flush_all()


@admin.register(models.WebhookQueuedCall)
class WebhookQueueAdmin(ModelAdmin):
    list_display = ('webhook', 'error_code', 'error_msg', 'created', 'updated')
    list_display_links = ('error_code', 'error_msg', 'created', 'updated')
    list_filter = ('webhook', 'error_code', 'created', 'updated')
    ordering = ('updated',)
    actions = [flush_queue_now]
