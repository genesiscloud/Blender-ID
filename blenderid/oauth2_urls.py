""""
New URL mapping to be compatible with Blender Cloud and other Blender ID users.

This mapping uses optional trailing slashes, and thus adheres better to RFC 6749.
I've also removed the "management" URLs, as we use the admin interface for that.
"""
# TODO(Sybren): move this file into bid_main, or move OAuth2 views into their own app.

from django.conf.urls import url

from oauth2_provider import views as default_oauth2_views
from bid_main.views import oauth2

app_name = 'oauth2_provider'
urlpatterns = (
    url(r'^authorize/?$', oauth2.AuthorizationView.as_view(), name="authorize"),
    url(r'^token/?$', default_oauth2_views.TokenView.as_view(), name="token"),
    url(r'^revoke/?$', default_oauth2_views.RevokeTokenView.as_view(), name="revoke-token"),
)
