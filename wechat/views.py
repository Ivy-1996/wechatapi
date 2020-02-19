from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet, GenericViewSet
from rest_framework.mixins import RetrieveModelMixin, CreateModelMixin

from django_redis import get_redis_connection

from wechat.core.bot import ForwardMessageBot
from wechat.core.authentication import AccessTokenAuthentication
from wechat.core import pkl_path

from wechat import serializers, models
from wechat.core import utils

import threading
import time
import os


class LoginView(APIView):
    bot_class = ForwardMessageBot

    authentication_classes = [AccessTokenAuthentication]

    def get(self, request, *args, **kwargs):
        assert self.bot_class is not None, 'bot_class不能为`None`'
        # 创建线程
        flag = time.time()
        login = threading.Thread(target=self.bot_login, args=(flag,))
        login.start()
        # 递归获取二维码
        response = self.get_response(flag)
        # byte 转字符串
        response = {k.decode(): v.decode() for k, v in response.items()}
        # 将键名改过来,便于登陆查询
        self.rename_redis_key(flag)
        return Response(response)

    def bot_login(self, flag):
        obj = self.bot_class(request=self.request, flag=flag)
        # 永久存储puid
        obj.enable_puid(os.path.join(pkl_path, f'{self.request.auth.app_id}.pkl'))

    def get_response(self, flag):
        time.sleep(0.01)
        coon = get_redis_connection('default')
        qrcode = coon.hgetall(flag)
        return qrcode if qrcode else self.get_response(flag)

    @staticmethod
    def rename_redis_key(flag):
        coon = get_redis_connection('default')
        uuid = coon.hget(flag, 'uuid')
        coon.rename(flag, uuid)


class CheckLoginView(APIView):
    """检查登陆状态"""
    authentication_classes = [AccessTokenAuthentication]

    def get(self, request, *args, **kwargs):
        serializer = serializers.CheckLoginSerializer(data=request.GET, context={'request': request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class FriendsReadOnlyModelViewSet(ReadOnlyModelViewSet):
    """好友列表查询接口"""
    serializer_class = serializers.WxUserModelModelSerializer
    authentication_classes = [AccessTokenAuthentication]

    def get_queryset(self):
        return self.request.user.friends.all()


class GroupsReadOnlyModelViewSet(ReadOnlyModelViewSet):
    """群查询接口"""
    authentication_classes = [AccessTokenAuthentication]
    serializer_class = serializers.WxGroupModelModelSerializer

    def get_queryset(self):
        return self.request.user.wxgroupmodel_set.all()


class GroupsMembersRetrieveModelMixinViewSet(RetrieveModelMixin, GenericViewSet):
    """群成员查询接口"""
    serializer_class = serializers.WxGroupMembersSerializer
    authentication_classes = [AccessTokenAuthentication]

    def get_queryset(self):
        return self.request.user.wxgroupmodel_set.all()

    def get_object(self):
        """修改`get_object`的返回结果,让`retrieve`调用"""
        instance = super().get_object()
        return instance.members.all()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        queryset = self.filter_queryset(instance)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class MpReadOnlyModelViewSet(ReadOnlyModelViewSet):
    """微信公众号查询接口"""
    serializer_class = serializers.WxMpsModelModelSerializer
    authentication_classes = [AccessTokenAuthentication]

    def get_queryset(self):
        return self.request.user.wxmpsmodel_set.all()


class MessageReadOnlyModelViewSet(ReadOnlyModelViewSet):
    """聊天记录查询接口"""
    serializer_class = serializers.MessageReadModelSerializer
    authentication_classes = [AccessTokenAuthentication]
    queryset = models.MessageModel.objects.all()
    filterset_fields = ['type', 'create_time', 'receive_time', 'is_at', 'sender_puid', 'receiver_puid']

    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user)


class AccessTokenView(APIView):
    """获取access token"""

    def get(self, request, *args, **kwargs):
        serializer = serializers.AccessTokenSerializer(data=request.GET)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class SendMessageView(CreateModelMixin, GenericViewSet):
    """主动发送消息"""

    serializer_class = serializers.SendMessageSerializer
    authentication_classes = [AccessTokenAuthentication]


class UpdateUserInfoView(APIView):
    """主动更新列表信息"""
    authentication_classes = [AccessTokenAuthentication]

    def get(self, request, *args, **kwargs):
        try:
            utils.update_app_info_by_view(request)
        except AssertionError as e:
            return Response({'errmsg': e.__str__()})
        return Response({'msg': '更新成功!'})
