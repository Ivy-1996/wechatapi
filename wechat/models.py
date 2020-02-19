from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

from wxpy.api.bot import User, Group, MP

from io import BytesIO

import uuid


# Create your models here.


class AppModel(models.Model):
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
    app_name = models.CharField(max_length=50, unique=True)
    app_id = models.CharField(max_length=32)
    app_secret = models.CharField(max_length=32)
    token = models.CharField(max_length=32)
    bind = models.OneToOneField('WxUserModel', on_delete=models.CASCADE, null=True)

    class Meta:
        verbose_name = verbose_name_plural = '微信应用'

    def __str__(self):
        return self.app_name

    @classmethod
    def create_app(cls):
        app_id, app_secret = uuid.uuid4().__str__(), uuid.uuid1().hex
        try:
            cls.objects.get(app_id=app_id)
        except cls.DoesNotExist:
            return app_id, app_secret
        return cls.create_app()


class ForwardMessageConfModel(models.Model):
    app = models.OneToOneField('AppModel', on_delete=models.CASCADE)
    url = models.URLField()

    class Meta:
        verbose_name = verbose_name_plural = '转发配置表'

    def __str__(self):
        return self.app.app_name


class ForwardMessageLog(models.Model):
    app = models.ForeignKey('AppModel', on_delete=models.CASCADE)
    content = models.CharField(max_length=255)
    create_time = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = verbose_name_plural = '转发log表'


class WxUserModel(models.Model):
    SEX_CHOICES = (
        (1, '男'),
        (2, '女')
    )
    puid = models.CharField(max_length=15, primary_key=True, help_text='微信用户的外键', verbose_name='PUID')
    name = models.CharField(max_length=32, verbose_name='名称', null=True)
    nick_name = models.CharField(max_length=32, verbose_name='昵称', null=True)
    user_name = models.CharField(max_length=80, verbose_name='用户名', null=True)
    remark_name = models.CharField(max_length=32, verbose_name='备注名', null=True)
    avatar = models.ImageField(verbose_name="头像", upload_to="media/avatar/users/%Y/%m/%d")
    signature = models.CharField(max_length=255, verbose_name="签名", null=True)
    sex = models.IntegerField(choices=SEX_CHOICES, verbose_name="性别", null=True)
    province = models.CharField(max_length=15, verbose_name="省", null=True)
    city = models.CharField(max_length=15, verbose_name="市", null=True)
    friends = models.ManyToManyField('self', verbose_name='好友列表', related_name='friends')

    senders = GenericRelation('MessageModel')

    def __str__(self):
        return self.name

    @classmethod
    def get_user(cls, bot: User):
        try:
            obj = cls.objects.get(puid=bot.puid)
        except cls.DoesNotExist:
            obj = cls.objects.create(
                puid=bot.puid,
                name=bot.name,
                nick_name=bot.nick_name,
                user_name=bot.user_name,
                remark_name=bot.remark_name,
                signature=bot.signature,
                sex=bot.sex,
                province=bot.province,
                city=bot.city,
            )
            obj.avatar.save(name=f'{bot.puid}.jpg', content=BytesIO(bot.get_avatar()))
        return obj

    class Meta:
        verbose_name_plural = verbose_name = '微信用户'


class WxGroupModel(models.Model):
    puid = models.CharField(max_length=15, primary_key=True)
    name = models.CharField(max_length=32, verbose_name='名称')
    nick_name = models.CharField(max_length=32, verbose_name='昵称')
    user_name = models.CharField(max_length=80)
    avatar = models.ImageField(verbose_name='头像', upload_to="media/avatar/groups/%Y/%m/%d")
    members = models.ManyToManyField(WxUserModel, related_name='members', verbose_name='群员')
    owner = models.ForeignKey(WxUserModel, on_delete=models.CASCADE, null=True, verbose_name='群归属')

    senders = GenericRelation('MessageModel')

    def __str__(self):
        return self.name

    @classmethod
    def get_group(cls, group: Group):
        try:
            obj = cls.objects.get(puid=group.puid)
        except cls.DoesNotExist:
            obj = cls.objects.create(
                puid=group.puid,
                name=group.name,
                nick_name=group.nick_name,
                user_name=group.user_name,
                owner=WxUserModel.get_user(group.bot.self)
            )
            obj.avatar.save(name=f'{group.puid}.jpg', content=BytesIO(group.get_avatar()))
        return obj

    class Meta:
        verbose_name_plural = verbose_name = '微信群组'


class WxMpsModel(models.Model):
    puid = models.CharField(max_length=15, primary_key=True)
    name = models.CharField(max_length=32, verbose_name='名称')
    nick_name = models.CharField(max_length=32, verbose_name='昵称')
    province = models.CharField(max_length=15, verbose_name="省", null=True)
    city = models.CharField(max_length=15, verbose_name="市", null=True)
    signature = models.CharField(max_length=255, verbose_name="签名", null=True)
    owner = models.ForeignKey(WxUserModel, on_delete=models.SET_NULL, null=True, verbose_name='群归属')

    class Meta:
        verbose_name_plural = verbose_name = '微信公众号'

    @classmethod
    def get_mp(cls, mp: MP):
        try:
            obj = cls.objects.get(puid=mp.puid)
        except cls.DoesNotExist:
            obj = cls.objects.create(
                puid=mp.puid,
                name=mp.name,
                nick_name=mp.nick_name,
                province=mp.province,
                city=mp.city,
                signature=mp.signature,
                owner=WxUserModel.get_user(mp.bot.self)
            )
        return obj

    def __str__(self):
        return self.name


class MessageModel(models.Model):
    TYPE_CHOICES = (
        ('Text', '文本'),
        ('Map', '位置'),
        ('Card', '名片'),
        ('Note', '提示'),
        ('Sharing', '分享'),
        ('Picture', '图片'),
        ('Recording', '语音'),
        ('Attachment', '文件'),
        ('Video', '视频'),
        ('Friends', '好友请求'),
        ('System', '系统'),
    )

    id = models.BigIntegerField(primary_key=True)
    type = models.CharField(max_length=15, choices=TYPE_CHOICES, verbose_name='消息类型')
    create_time = models.DateTimeField(verbose_name='创建时间')
    receive_time = models.DateTimeField(verbose_name='接受时间')
    is_at = models.BooleanField(default=False, null=True, verbose_name='是否@')
    member = models.ForeignKey(WxUserModel, on_delete=models.CASCADE, null=True, related_name='msg_members')

    owner = models.ForeignKey(WxUserModel, on_delete=models.SET_NULL, null=True, related_name='msg_owner',
                              verbose_name='信息的拥有者')

    sender_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='senders')
    sender_puid = models.CharField(max_length=10)
    receiver_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='receivers')
    receiver_puid = models.CharField(max_length=10)

    sender = GenericForeignKey('sender_content_type', 'sender_puid')
    receiver = GenericForeignKey('receiver_content_type', 'receiver_puid')

    class Meta:
        verbose_name = verbose_name_plural = '消息记录'

    def __str__(self):
        return f'{self.type}-{self.owner.name}'


class BaseMessage(models.Model):
    message = models.OneToOneField(MessageModel, on_delete=models.CASCADE, primary_key=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.message.__str__()


class TextMessage(BaseMessage):
    text = models.CharField(max_length=2048, verbose_name='文本内容')

    class Meta:
        verbose_name = verbose_name_plural = '文本消息'

    def __str__(self):
        return self.text


class MapMessage(BaseMessage):
    x = models.FloatField()
    y = models.FloatField()
    scale = models.IntegerField()
    label = models.CharField(max_length=255)
    maptype = models.IntegerField()
    poiname = models.CharField(max_length=255)
    poiid = models.CharField(max_length=255, blank=True)
    url = models.CharField(max_length=500)
    text = models.CharField(max_length=255)

    class Meta:
        verbose_name = verbose_name_plural = '位置消息'

    def __str__(self):
        return self.label


class SharingMessage(BaseMessage):
    url = models.URLField(max_length=500)
    text = models.CharField(max_length=50)

    class Meta:
        verbose_name = verbose_name_plural = '分享消息'

    def __str__(self):
        return self.text


class PictureMessage(BaseMessage):
    image = models.ImageField(verbose_name='头像', upload_to="media/image/%Y/%m/%d")
    img_height = models.IntegerField(verbose_name='图片高度', null=True)
    img_width = models.IntegerField(verbose_name='图片宽度', null=True)

    class Meta:
        verbose_name = verbose_name_plural = '图片消息'


class RecordingMessage(BaseMessage):
    voice_length = models.BigIntegerField(null=True, verbose_name='录音时间')
    record = models.FileField(upload_to='media/record/%Y/%m/%d')

    class Meta:
        verbose_name = verbose_name_plural = '录音消息'


class AttachmentMessage(BaseMessage):
    file_size = models.CharField(max_length=20, null=True)
    file = models.FileField(max_length=500, upload_to='media/file/%Y/%m/%d')

    class Meta:
        verbose_name = verbose_name_plural = '文件消息'


class VideoMessage(BaseMessage):
    play_length = models.IntegerField(null=True)
    video = models.FileField(upload_to='media/video/%Y/%m/%d')

    class Meta:
        verbose_name = verbose_name_plural = '视频消息'


class CardMessage(BaseMessage):
    SEX_CHOICES = (
        (1, '男'),
        (2, '女')
    )
    username = models.CharField(max_length=50)
    nickname = models.CharField(max_length=50, verbose_name='昵称')
    alias = models.CharField(max_length=50, verbose_name='微信号')
    province = models.CharField(max_length=20)
    city = models.CharField(max_length=20)
    sign = models.CharField(max_length=255)
    sex = models.SmallIntegerField(choices=SEX_CHOICES, null=True)
    avatar = models.URLField()

    class Meta:
        verbose_name = verbose_name_plural = '名片消息'


class NoteMessage(BaseMessage):
    text = models.CharField(max_length=255)

    class Meta:
        verbose_name = verbose_name_plural = '提示消息'
