""""
New URL mapping to be compatible with Blender Cloud and other Blender ID users.

This mapping uses optional trailing slashes, and thus adheres better to RFC 6749.
I've also removed the "management" URLs, as we use the admin interface for that.
"""

from __future__ import absolute_import
from django.conf.urls import url

from oauth2_provider import views as default_oauth2_views
from bid_main import oauth2_views

urlpatterns = (
    url(r'^authorize/?$', oauth2_views.AuthorizationView.as_view(), name="authorize"),
    url(r'^token/?$', default_oauth2_views.TokenView.as_view(), name="token"),
    url(r'^revoke/?$', default_oauth2_views.RevokeTokenView.as_view(), name="revoke-token"),
)
