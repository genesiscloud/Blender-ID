"""User avatar thumbnail rendering."""
import typing

from django import template
from django.conf import settings
from django.template import loader
from django.template.context import BaseContext
from django.utils.safestring import mark_safe

import bid_main.models

register = template.Library()


@register.simple_tag(takes_context=True)
def avatar(context: BaseContext,
           user: typing.Optional[bid_main.models.User] = None,
           size=0) -> str:
    """Render the user's avatar as JPEG thumbnail.

    :param context:
    :param user: the user to render the avatar for, or None for the currently logged-in user.
    :param size: the size of the avatar, or 0 for the default size.
    """

    size = size or settings.AVATAR_DEFAULT_SIZE_PIXELS

    template_ctx = {
        'user': user or context.get('user'),
        'avatar_size_str': f'{size}x{size}',
        'avatar_size': size,
        'default_avatar': settings.AVATAR_DEFAULT_FILENAME,
    }
    content = loader.render_to_string('bid_main/templatetags/avatar/avatar.html', template_ctx)

    return mark_safe(content)
