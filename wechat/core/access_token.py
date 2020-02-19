from django.conf import settings

from wechat.models import AppModel

from django_redis import get_redis_connection

from . import exception

import uuid


class AccessToken:
    model = AppModel
    expire_in = getattr(settings, 'ACCESS_TOKEN_EXPIRE_IN', 3600 * 2)

    @classmethod
    def create_access_token(cls, app_id, app_secret):
        """创建token"""
        cls.get_model(app_id=app_id, app_secret=app_secret)

        coon = get_redis_connection('default')

        token = uuid.uuid4().__str__()

        coon.set(token, app_id)

        coon.expire(token, cls.expire_in)

        key = f'{app_id}_access_token'

        # 把原来的旧的删掉,减少内存的占用
        raw_token = coon.get(key)

        if raw_token:
            coon.delete(raw_token)

        # 创建反向的查询,即使生成了多个token也只会有唯一一个生效
        coon.set(key, token)
        return token

    @classmethod
    def check_access_token(cls, token):
        """检验token"""
        coon = get_redis_connection('default')
        app_id = coon.get(token)
        if app_id:

            app_id = app_id.decode()

            app = cls.get_model(app_id=app_id)

            # 获取真实的有效的token
            real_token = coon.get(f'{app_id}_access_token').decode()
            # 检查当前的token和真实的token是否一致
            if real_token == token:
                return app

        raise exception.InvalidTokenException()

    @classmethod
    def get_model(cls, **kwargs):
        """获取app模型"""
        try:
            app = cls.model.objects.get(**kwargs)
        except cls.model.DoesNotExist:
            raise exception.AppDoesNotExistException()
        return app
