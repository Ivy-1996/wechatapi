from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from wechat.core.access_token import AccessToken
from wechat.core import exception
from wechat import serializers


class SignatureAuthentication(BaseAuthentication):

    def authenticate(self, request):
        """签名 验证类"""
        serializer = serializers.SignatureSerializer(data=request.GET)
        if serializer.is_valid():
            app = serializer.validated_data
            return app.bind, app
        raise AuthenticationFailed(serializer.errors)


class AccessTokenAuthentication(BaseAuthentication):
    """access-token 验证类"""

    def authenticate(self, request):
        access_token = request.GET.get('access_token')
        if access_token:
            try:
                app = AccessToken.check_access_token(access_token)
            except exception.InvalidTokenException:
                raise AuthenticationFailed({'errmsg': '无效的token或已过期!'})
            return app.bind, app
        raise AuthenticationFailed({'errmsg': '无效的身份信息!'})
