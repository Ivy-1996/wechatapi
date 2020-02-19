from django.conf import settings

from rest_framework.request import Request

from django_redis import get_redis_connection

from wxpy import Bot
from wxpy.api.messages import Messages, MessageConfig

from wechat.core.handles import SaveMessageHandle, ForwardMessageHandle

from . import message
from .. import models
from . import exception
from .const import *
from . import utils

import os
import time
import requests
import re


class BaseMessageBot(Bot):
    default_max_history = 500

    def __init__(self, console_qr=False, qr_path=None, qr_callback=None, login_callback=None,
                 logout_callback=None, scan_callback=None, flag=None, **kwargs):

        self.request: Request = kwargs.pop('request')

        # 初始化函数
        login_callback = login_callback or self.login_callback

        logout_callback = logout_callback or self.loginout_callback

        cache_path = self.default_cache_path

        qr_callback = qr_callback or self.qr_callback

        self.scan_callback = scan_callback or self.default_scan_callback

        self.flag = flag

        self.alive_key = utils.get_alive_key(self.request)

        super().__init__(cache_path=cache_path, console_qr=console_qr, qr_path=qr_path, qr_callback=qr_callback,
                         login_callback=login_callback,
                         logout_callback=logout_callback)

        self.max_history = getattr(settings, 'MAX_HISTORY', self.default_max_history)

        self.messages = Messages(max_history=self.max_history)

        self.kwrags = kwargs

        self.initial()

    def login_callback(self):
        print(f'{self.request.user or "匿名用户"}登陆成功!')
        """"""
        coon = get_redis_connection('default')

        coon.set(self.alive_key, 1)

    def loginout_callback(self):
        print(f'{self.request.user}已退出!')
        """loginout  将登陆状态改为False"""
        coon = get_redis_connection('default')

        coon.set(self.alive_key, 0)

    def qr_callback(self, uuid, status, qrcode):
        """默认的二维码回调函数"""

        self._qr_callback(uuid, status, qrcode)

    def default_scan_callback(self, uuid, status):

        if status == '201':
            # 获取扫描之后的用户的头像
            url = 'https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login'
            params = {
                'loginicon': 'true',  # 这个参数必须要有,否则不会显示二维码
                'uuid': uuid,
                'tip': '1',
                '_': int(time.time())
            }

            # 请求当前用户的头像
            resp = requests.get(url, params=params, headers=Header).text
            """window.code=201;window.userAvatar = 'data:img/jpg;base64,<base64字符串>';"""

            # 正则提取base64字符串
            reg = "base64,(.*?)'"

            content = re.findall(reg, resp, re.S)[0]

            # 存到redis里
            coon = get_redis_connection('default')
            coon.hset(uuid, 'avatar', content)

    def login_init(self, uuid, status, name=None):
        # 连接redis
        # 将登陆时传的标记获取
        # 存入三个属性存入redis
        coon = get_redis_connection('default')
        name = name or self.flag

        coon.hset(name, 'uuid', uuid)
        coon.hset(name, 'status', status)
        coon.hset(name, 'qrcode', f'https://login.weixin.qq.com/qrcode/{uuid}')
        coon.expire(name, 60 * 10)

    def _qr_callback(self, uuid, status, qrcode):
        """根据不同的状态码执行不同的操作"""
        if status == '0':
            return self.login_init(uuid, status)
        if status == '201' or status == '200':
            self.scan_callback(uuid, status)
        elif status == '400':
            raise exception.LoginTimeOutException()

        # 将key换成uuid
        self.login_init(uuid, status, uuid)

    @property
    def default_cache_path(self):
        """获取登陆后的缓存路径"""
        cache_path = utils.get_cache_path(self.request)
        # 如果原先存在,那就删除原来的,不然程序会卡在那里
        if os.path.exists(cache_path):
            os.remove(cache_path)
        return cache_path

    def initial(self):
        pass

    def enable_puid(self, path='wxpy_puid.pkl'):
        result = super().enable_puid(path)
        # 绑定用户
        self.bind()
        return result

    def bind(self):
        if self.request.user is None:
            app = self.request.auth
            user = models.WxUserModel.get_user(self.self)
            app.bind = user
            app.save()


class CacheBot(Bot):
    def __init__(self, console_qr=False, qr_path=None, qr_callback=None, login_callback=None,
                 logout_callback=None, **kwargs):
        self.request: Request = kwargs.pop('request')

        cache_path = utils.get_cache_path(self.request)

        super(CacheBot, self).__init__(cache_path=cache_path, console_qr=console_qr, qr_callback=qr_callback,
                                       qr_path=qr_path, login_callback=login_callback, logout_callback=logout_callback)


class DefaultBot(BaseMessageBot):
    default_message_conf = {'chats': None, 'msg_types': None, 'except_self': False, 'run_async': True,
                            'enabled': True}
    handler_classes = list()

    def initial(self):
        super().initial()
        self.add_register()

    def add_register(self):
        message_conf = self.kwrags.get('message_conf', self.default_message_conf)
        self.registered.append(MessageConfig(bot=self, func=self.listen, **message_conf))

    def listen(self, msg):
        context = self.get_context()
        for handle_class in self.handler_classes:
            handle = handle_class(msg, context)
            handle.dispatch()

    def get_context(self):
        return {
            'kwargs': self.kwrags,
            'request': self.request
        }


class ModelMessageBot(DefaultBot):
    parse_message_class = message.ModelParseMessage

    def listen(self, msg):
        msg = self.process_msg(msg)
        return super(ModelMessageBot, self).listen(msg)

    def process_msg(self, msg):
        assert self.parse_message_class is not None, '类属性`parse_message_class`不可以为`None`,或者你可以重写这个方法'
        context = self.get_context()
        return self.parse_message_class(msg, context=context)


class SaveModelMessageBot(ModelMessageBot):
    handler_classes = [SaveMessageHandle]


class ForwardMessageBot(ModelMessageBot):
    handler_classes = [ForwardMessageHandle]
