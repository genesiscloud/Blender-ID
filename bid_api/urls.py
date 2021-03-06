from django.conf.urls import url

from .views import info, badger, create_user, authenticate

app_name = 'bid_api'
urlpatterns = [
    url(r'^user$', info.user_info, name='user'),
    url(r'^me$', info.user_info),
    url(r'^user/(?P<user_id>\d+)$', info.UserInfoView.as_view(), name='user-info-by-id'),
    url(r'^user/(?P<user_id>\d+)/avatar$', info.UserAvatarView.as_view(), name='user-avatar'),
    url(r'^badges/(?P<user_id>\d+)$', info.UserBadgeView.as_view(), name='user-badges-by-id'),
    url(r'^badges/(?P<user_id>\d+)/html$', info.BadgesHTMLView.as_view(), name='user-badges-html'),
    url(r'^badges/(?P<user_id>\d+)/html/(?P<size>[a-z])$', info.BadgesHTMLView.as_view(),
        name='user-badges-html'),
    url(r'^stats$', info.StatsView.as_view(), name='stats'),
    url(r'^badger/grant/(?P<badge>[^/]+)/(?P<email_or_uid>[^/]+)$',
        badger.BadgerView.as_view(action='grant'), name='badger_grant'),
    url(r'^badger/revoke/(?P<badge>[^/]+)/(?P<email_or_uid>[^/]+)$',
        badger.BadgerView.as_view(action='revoke'), name='badger_revoke'),
    url(r'^check-user/(?P<email>[^/]+)$', create_user.CheckUserView.as_view(), name='check_user'),
    url(r'^create-user/?$', create_user.CreateUserView.as_view(), name='create_user'),
    url(r'^authenticate/?$', authenticate.AuthenticateView.as_view(), name='authenticate'),
]

# noinspection PyUnresolvedReferences
from . import signals as _
