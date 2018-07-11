"""
Renders badges.
"""

from django import template
from django.template.context import BaseContext
from django.template import loader
from django.utils.safestring import mark_safe

import bid_main.models

register = template.Library()


@register.simple_tag(takes_context=True)
def render_badge(context: BaseContext, the_badge: bid_main.models.Role) -> str:
    sub_ctx = context.flatten()
    sub_ctx['badge'] = the_badge

    content = loader.render_to_string('bid_main/templatetags/badges/render_badge.html', sub_ctx)
    return mark_safe(content)
