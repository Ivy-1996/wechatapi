from wechat.serializers import MessageReadModelSerializer
from wechat.models import ForwardMessageConfModel, ForwardMessageLog

from .message import ModelParseMessage

from . import exception

import requests


class BaseHandle:
    def __init__(self, message, context: dict):
        self.message = message
        self.kwargs = context.pop('kwargs')
        self.request = context.pop('request')

    def dispatch(self):
        """根据请求消息的类型进行方法匹配,如果没有定义的方法,那么就行默认的方法"""
        message_type = self.message.type
        handle = getattr(self, message_type.lower(), self.default_handle)
        return handle()

    def default_handle(self, **kwargs):
        """默认的消息执行方法"""
        return self.do_nothing(**kwargs)

    def do_nothing(self, **kwargs):
        pass


class SaveMessageHandle(BaseHandle):

    def __init__(self, message, context: dict):
        super(SaveMessageHandle, self).__init__(message, context)

        assert isinstance(self.message,
                          ModelParseMessage), f'`{self.__class__.__name__}` `message` 必须是`ModelParseMessage`的实例对象'

    def default_handle(self, **kwargs):
        serializer = self.message.get_serializer()
        data = serializer.data
        print(data)
        # 默认是执行`message`对象的`serializer`对象的保存消息方法
        return serializer.message_create(data)


class ForwardMessageHandle(SaveMessageHandle):

    def default_handle(self, **kwargs):
        """重写父类的默认分发消息的方法"""

        # 执行父类的`default_handle`保存信息
        obj = super(ForwardMessageHandle, self).default_handle(**kwargs)

        # 序列化保存后的模型对象
        serializer = MessageReadModelSerializer(instance=obj.message)
        data = serializer.data

        # 开始转发
        forward = self.get_forward()
        self.forward(forward, data)

    def get_forward(self) -> ForwardMessageConfModel:
        """根据app获取转发配置"""
        try:
            forward_conf = ForwardMessageConfModel.objects.get(app=self.request.auth)
        except ForwardMessageConfModel.DoesNotExist:
            raise exception.ForwardUrlDoesNotExistException(f'{self.request.auth.app_name}应用没有配置ForwardUrl')
        return forward_conf

    @staticmethod
    def forward(forward_conf, data):
        """转发"""
        app, url = forward_conf.app, forward_conf.url

        try:
            resp = requests.post(url, json=data)
        except Exception as e:
            # 保存错误信息
            ForwardMessageLog.objects.create(app=app, content=e.args)
            # 继续向上抛出异常
            raise

        if resp.text != 'ok':
            # 保存错误信息
            content = '发送失败!'
            ForwardMessageLog.objects.create(app=app, content=content)
            raise exception.ForwardFailError(content)
        print('forward success')
