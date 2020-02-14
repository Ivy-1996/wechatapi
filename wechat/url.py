from django.urls import path, re_path
from django.conf import settings
from django.views.static import serve

from rest_framework.routers import DefaultRouter

from . import views

route = DefaultRouter(trailing_slash=False)

route.register('friends', viewset=views.FriendsReadOnlyModelViewSet, basename='friends')
route.register('groups', viewset=views.GroupsReadOnlyModelViewSet, basename='groups')
route.register('members', viewset=views.GroupsMembersRetrieveModelMixinViewSet, basename='members')
route.register('mps', viewset=views.MpReadOnlyModelViewSet, basename='members')
route.register('messages', viewset=views.MessageReadOnlyModelViewSet, basename='messages')
route.register('send-message', viewset=views.SendMessageView, basename='send-message')

urlpatterns = [
    re_path('^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_PATH}),
    path('login', views.LoginView.as_view()),
    path('check-login', views.CheckLoginView.as_view()),
    path('access-token', views.AccessTokenView.as_view()),
    path('update', views.UpdateUserInfoView.as_view()),
]

urlpatterns += route.urls
