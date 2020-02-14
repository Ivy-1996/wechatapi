from wxpy import Group

from wechat import serializers


class BaseParseMessage:
    def __init__(self, message, context):
        self.message = message
        self.context = context
        self.kwargs = context.pop('kwargs', None)
        self.request = context.pop('request', None)

    def __getattr__(self, item):
        try:
            return self.__getattribute__(item)
        except AttributeError:
            return getattr(self.message, item)


class ModelParseMessage(BaseParseMessage):
    serializer_class_route = {
        'text': serializers.TextMessageModelSerializer,
        'map': serializers.MapMessageModelSerializer,
        'sharing': serializers.SharingMessageModelSerializer,
        'picture': serializers.PictureMessageModelSerializer,
        'recording': serializers.RecordingMessageModelSerializer,
        'video': serializers.VideoMessageModelSerializer,
        'attachment': serializers.AttachmentMessageModelSerializer,
        'card': serializers.CardMessageModelSerializer,
        'note': serializers.NoteMessageModelSerializer,
    }

    def get_serializer_class(self):
        return self.serializer_class_route.get(self.message.type.lower())

    def get_serializer(self):
        serializer = self.get_serializer_class()
        return serializer(instance=self.message, context=self.context)


class SendMessageParser(ModelParseMessage):

    @property
    def is_at(self):
        if isinstance(self.message.receiver, Group):
            return False

    @property
    def member(self):
        if isinstance(self.message.receiver, Group):
            return self.message.bot.self
