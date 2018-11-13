from django.conf.urls import url

from . import views

app_name = 'bid_addon_support'
urlpatterns = [
    url(r'^u/$', views.index, name='index'),
    url(r'^u/identify$', views.VerifyIdentityView.as_view(), name='identify'),
    url(r'^u/delete_token$', views.DeleteTokenView.as_view(), name='delete_token'),
    url(r'^u/validate_token$', views.ValidateTokenView.as_view(), name='validate_token'),
    url(r'^subclients/create_token', views.SubclientCreateToken.as_view(),
        name='subclient_create_token'),
    url(r'^subclients/revoke_token', views.DeleteTokenView.as_view(),
        name='subclient_revoke_token'),
]
