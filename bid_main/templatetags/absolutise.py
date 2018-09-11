"""
Turns relative URLs into absolute URLs.
"""

from django import template
from django.http import HttpRequest

register = template.Library()


@register.filter
def absolutise(the_url: str, request: HttpRequest) -> str:
    return request.build_absolute_uri(the_url)
