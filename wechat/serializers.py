import os
from io import BytesIO

from django.db import transaction
from django.utils.functional import cached_property

from django_redis import get_redis_connection

from collections import OrderedDict

from wxpy import User, Group, MP

from rest_framework import serializers

from wechat.core.access_token import AccessToken
from wechat.core import exception

from . import models
from .core import utils

import time
import hashlib
import re


class SignatureSerializer(serializers.Serializer):
    app_id = serializers.CharField()
    app_secret = serializers.CharField()
    timestamp = serializers.IntegerField()
    signature = serializers.CharField()

    def validate_timestamp(self, attrs):
        """验证时间戳的合法性"""
        now = time.time()
        if now - attrs > 3:
            raise serializers.ValidationError('invalid timestamp')
        return attrs

    def validate(self, attrs):
        timestamp = attrs.get('timestamp')
        signature = attrs.get('signature')
        app = self.get_app(attrs)
        # 验证签名的正确性
        real_signature = self.get_real_signature(timestamp, app)
        if real_signature != signature:
            raise serializers.ValidationError({'signature': 'invalid signature'})
        return app

    def get_real_signature(self, timestamp: int, app: models.AppModel, ):
        """获取真实的签名"""
        token = app.token
        item = [token, str(timestamp)]
        item.sort()
        string = ''.join(item)
        return hashlib.sha1(string.encode()).hexdigest()

    def get_app(self, attr):
        app_id = attr.get('app_id')
        app_secret = attr.get('app_secret')
        try:
            app = models.AppModel.objects.get(app_id=app_id, app_secret=app_secret)
        except models.AppModel.DoesNotExist:
            raise serializers.ValidationError({'app_id': 'invalid appid'})
        return app


class CheckLoginSerializer(serializers.Serializer):
    uuid = serializers.CharField()

    def validate(self, attrs):
        uuid = attrs.get('uuid')
        coon = get_redis_connection('default')

        response = OrderedDict()

        response['status'] = coon.hget(uuid, 'status')
        request = self.context.get('request')
        response['avatar'] = coon.hget(uuid, 'avatar')
        key = f'{request.auth.app_id}_alive'
        response['alive'] = coon.get(key)

        return response


class WxUserModelModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.WxUserModel
        exclude = ['friends']


class WxGroupModelModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.WxGroupModel
        exclude = ['members']


class WxGroupMembersSerializer(WxUserModelModelSerializer):
    pass


class WxMpsModelModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.WxMpsModel
        exclude = ['owner']


class BaseModelSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        """将message对象转换为dict对象"""
        if isinstance(instance, models.models.Model):
            return super().to_representation(instance)
        return self.to_message_representation(instance)

    @transaction.atomic
    def to_message_representation(self, instance):
        ret = OrderedDict()
        # 获取所有的字段
        fields = self._readable_fields

        save_point = transaction.savepoint()

        for field in fields:
            field_name = field.field_name

            # 先判断有没有自己实现获取属性的方法
            if hasattr(self, f'get_{field_name}_attr'):
                handle = getattr(self, f'get_{field_name}_attr')
                ret = handle(ret)
                continue

            # 尝试从`instance`中根据属性名获取属性值
            try:
                value = getattr(instance, field_name)
                ret[field_name] = value
            except AttributeError:
                transaction.savepoint_rollback(save_point)
                raise AttributeError(f'`instance`没有{field_name}这个属性,你可以定义`get_{field_name}_attr`来获取对应的值')

        return ret

    @property
    def model(self):
        return self.Meta.model

    def message_create(self, data):
        return self.model.objects.create(**data)


class BaseMessageSerializer(BaseModelSerializer):
    def get_message_attr(self, ret):
        data = self.serializer.data
        data.update(self.get_extra_field())
        message = self.serializer.message_create(data)
        ret['message'] = message
        return ret

    @cached_property
    def serializer(self):
        return MessageModelSerializer(self.instance)

    def get_extra_field(self):
        """获取额外的数据"""
        ret = OrderedDict()
        ret = self.serializer.get_sender_attr(ret)
        ret = self.serializer.get_receiver_attr(ret)
        return ret


class MessageModelSerializer(BaseModelSerializer):
    """所有`message`的`OneToOne`类的序列化类"""

    class Meta:
        model = models.MessageModel
        exclude = ['sender_content_type', 'sender_puid', 'receiver_content_type', 'receiver_puid']

    def get_member_attr(self, ret):
        """获取member"""
        member = self.instance.member
        ret['member'] = models.WxUserModel.get_user(self.instance.member) if member else None
        return ret

    def get_owner_attr(self, ret):
        """获取owner"""
        ret['owner'] = models.WxUserModel.get_user(self.instance.bot.self)
        return ret

    def get_sender_attr(self, ret):
        """获取sender"""
        ret['sender'] = self.get_msg_relater(self.instance.sender)
        return ret

    def get_receiver_attr(self, ret):
        """获取receiver"""
        ret['receiver'] = self.get_msg_relater(self.instance.receiver)
        return ret

    @staticmethod
    def get_msg_relater(relater):
        """根据不同`message`对象来获取不同的model对象"""
        if isinstance(relater, MP):
            sender = models.WxMpsModel.get_mp(relater)
        elif isinstance(relater, Group):
            sender = models.WxGroupModel.get_group(relater)
        elif isinstance(relater, User):
            sender = models.WxUserModel.get_user(relater)
        else:
            raise Exception(f'{type(relater)}-未知的relater')
        return sender


class TextMessageModelSerializer(BaseMessageSerializer):
    class Meta:
        model = models.TextMessage
        fields = '__all__'


class MapMessageModelSerializer(BaseMessageSerializer):
    class Meta:
        model = models.MapMessage
        fields = '__all__'

    def get_x_attr(self, ret):
        ret['x'] = self.location.get('x')
        return ret

    def get_y_attr(self, ret):
        ret['y'] = self.location.get('y')
        return ret

    def get_scale_attr(self, ret):
        ret['scale'] = self.location.get('scale')
        return ret

    def get_label_attr(self, ret):
        ret['label'] = self.location.get('label')
        return ret

    def get_maptype_attr(self, ret):
        ret['maptype'] = self.location.get('maptype')
        return ret

    def get_poiname_attr(self, ret):
        ret['poiname'] = self.location.get('poiname')
        return ret

    def get_poiid_attr(self, ret):
        ret['poiid'] = self.location.get('poiid')
        return ret

    @cached_property
    def location(self):
        return self.instance.location


class SharingMessageModelSerializer(BaseMessageSerializer):
    class Meta:
        model = models.SharingMessage
        fields = '__all__'


class PictureMessageModelSerializer(BaseMessageSerializer):
    class Meta:
        model = models.PictureMessage
        fields = '__all__'

    def get_image_attr(self, ret):
        image = self.instance.get_file()
        ret['image'] = image
        return ret

    def message_create(self, data):
        image = data.pop('image')
        obj = super().message_create(data)
        obj.image.save(name=self.instance.file_name, content=BytesIO(image))
        return obj


class RecordingMessageModelSerializer(BaseMessageSerializer):
    class Meta:
        model = models.RecordingMessage
        fields = '__all__'

    def get_record_attr(self, ret):
        record = self.instance.get_file()
        ret['record'] = record
        return ret

    def message_create(self, data):
        record = data.pop('record')
        obj = super().message_create(data)
        obj.record.save(name=self.instance.file_name, content=BytesIO(record))
        return obj


class VideoMessageModelSerializer(BaseMessageSerializer):
    class Meta:
        model = models.VideoMessage
        fields = '__all__'

    def get_video_attr(self, ret):
        ret['video'] = self.instance.get_file()
        return ret

    def message_create(self, data):
        video = data.pop('video')
        obj = super().message_create(data)
        obj.video.save(name=self.instance.file_name, content=BytesIO(video))
        return obj


class AttachmentMessageModelSerializer(BaseMessageSerializer):
    class Meta:
        model = models.AttachmentMessage
        fields = '__all__'

    def get_file_attr(self, ret):
        ret['file'] = self.instance.get_file()
        return ret

    def message_create(self, data):
        file = data.pop('file')
        obj = super().message_create(data)
        obj.file.save(name=self.instance.file_name, content=BytesIO(file))
        return obj


class CardMessageModelSerializer(BaseMessageSerializer):
    class Meta:
        model = models.CardMessage
        fields = '__all__'

    @cached_property
    def raw_content(self):
        return self.instance.raw.get('Content')

    def get_username_attr(self, ret):
        username = self.re_search('username')
        ret['username'] = username
        return ret

    def get_nickname_attr(self, ret):
        nickname = self.re_search('nickname')
        ret['nickname'] = nickname
        return ret

    def get_alias_attr(self, ret):
        alias = self.re_search('alias')
        ret['alias'] = alias
        return ret

    def get_province_attr(self, ret):
        province = self.re_search('province')
        ret['province'] = province
        return ret

    def get_city_attr(self, ret):
        city = self.re_search('city')
        ret['city'] = city
        return ret

    def get_sign_attr(self, ret):
        sign = self.re_search('sign')
        ret['sign'] = sign
        return ret

    def get_sex_attr(self, ret):
        sex = self.re_search('sex')
        ret['sex'] = sex
        return ret

    def get_avatar_attr(self, ret):
        avatar = self.re_search('bigheadimgurl')
        ret['avatar'] = avatar
        return ret

    def re_search(self, attr=None, reg=None, extract_first=True):
        """正则匹配xml"""
        assert any([attr, reg]), '`attr` 和 `reg` 必须有一个为必填参数!'
        if attr:
            reg = f'{attr}="(.*?)"'
            result = re.findall(reg, self.raw_content)
            return result[0] if extract_first else result

        result = re.findall(reg, self.raw_content)
        return result[0] if extract_first else result


class NoteMessageModelSerializer(BaseMessageSerializer):
    class Meta:
        model = models.NoteMessage
        fields = '__all__'


class MessageReadModelSerializer(serializers.ModelSerializer):
    content = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()

    class Meta:
        model = models.MessageModel
        exclude = ['owner', 'sender_content_type', 'receiver_content_type']

        serializers_class_route = {
            'text': TextMessageModelSerializer,
            'map': MapMessageModelSerializer,
            'card': CardMessageModelSerializer,
            'sharing': SharingMessageModelSerializer,
            'picture': PictureMessageModelSerializer,
            'recording': RecordingMessageModelSerializer,
            'attachment': AttachmentMessageModelSerializer,
            'video': VideoMessageModelSerializer,
            'note': NoteMessageModelSerializer
        }

    def get_content(self, row):
        """
        `SerializerMethodField`的自定义方法
        """
        # 先获取当前消息的消息类型
        # 再根据消息类型获取对应的模型序列化类
        # 拿到序列化类之后在获取序列化类绑定的model模型
        # 获取模型名的全小写
        # 之后获取对应绑定的一对一的模型类
        # 最后拿到模型类,用序列化队像来反序列化返回数据
        msg_type = row.type.lower()
        serializers_class = self.get_serializers_class(msg_type)
        attr = self.get_relate_attr(serializers_class)
        relate_model = getattr(row, attr)
        serializer = serializers_class(instance=relate_model)
        return serializer.data

    def get_type(self, row):
        """返回发送接受者的类型信息"""
        return {
            'sender': row.sender.__class__.__name__.lower(),
            'receiver': row.receiver.__class__.__name__.lower()
        }

    def get_serializers_class(self, msg_type):
        return self.Meta.serializers_class_route.get(msg_type)

    def get_relate_attr(self, serializers_class):
        return serializers_class.Meta.model.__name__.lower()


class AccessTokenSerializer(serializers.Serializer):
    app_id = serializers.CharField()
    app_secret = serializers.CharField()

    def validate(self, attrs):
        app_id = attrs.get('app_id')
        app_secret = attrs.get('app_secret')
        try:
            token = AccessToken.create_access_token(app_id, app_secret)
        except exception.AppDoesNotExistException:
            raise serializers.ValidationError({'errmsg': '无效的app'})
        return {'access_token': token, 'expire_in': AccessToken.expire_in}


class SendMessageSerializer(serializers.Serializer):
    type = serializers.CharField()
    file = serializers.FileField(required=False)
    text = serializers.CharField(required=False)
    puid = serializers.CharField()

    @property
    def allow_type(self):
        return ['text', 'image', 'video', 'file', ]

    def validate_type(self, attr):
        if attr not in self.allow_type:
            raise serializers.ValidationError('非法的消息类型!')
        return attr

    def validate_file(self, attr):
        if attr:
            file_name = f'{time.time()}{attr.name}'
            with open(file_name, 'wb') as f:
                for line in attr.chunks():
                    f.write(line)
            return file_name
        return attr

    def validate(self, attrs):

        msg_type = attrs.get('type')
        file = attrs.get('file')
        text = attrs.get('text')
        puid = attrs.get('puid')
        # 检测数据的合法性
        self.validate_file_and_text(attrs)
        # 检验在线状态
        try:
            bot = utils.get_cache_bot(self.request)
        except AssertionError as e:
            raise serializers.ValidationError({'errmsg': e.__str__()})
        data = {'bot': bot, 'msg_type': msg_type, 'puid': puid, 'text': text, 'file_path': file}

        return data

    def validate_file_and_text(self, attrs):
        msg_type = attrs.get('type')
        file = attrs.get('file')
        text = attrs.get('text')
        if msg_type == 'text' and text is None:
            raise serializers.ValidationError({'errmsg': 'type为text时, text为必填参数！'})
        elif msg_type != 'text' and file is None:
            raise serializers.ValidationError({'errmsg': 'type不为text时, file为必填参数！'})

    def create(self, validated_data):
        """尝试发消息,如果不成功,则抛出异常,最后删除文件"""
        try:
            msg = utils.send_message(**validated_data)
        except exception.PUIDSearchError:
            raise serializers.ValidationError({'errmsg': '未找到对应uuid的匹配对象!'})
        finally:
            # 删除文件
            file_path = validated_data.pop('file_path')
            if file_path:
                os.remove(file_path)
        return self.save_message(msg)

    @cached_property
    def request(self):
        return self.context.get('request')

    @property
    def data(self):
        return getattr(self, 'response')

    def save_message(self, msg):

        """保存消息到数据库"""
        from wechat.core.message import SendMessageParser

        context = {'request': self.request, 'kwargs': {}}
        msg = SendMessageParser(msg, context)
        msg = SendMessageParser(msg, context)
        serializer = msg.get_serializer()
        msg_model_obj = serializer.message_create(serializer.data)
        message_serializer = MessageReadModelSerializer(msg_model_obj.message)
        response = message_serializer.data
        setattr(self, 'response', response)
        return response
