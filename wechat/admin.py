from django.contrib import admin
from django.utils.safestring import mark_safe

from . import models


# Register your models here.


@admin.register(models.AppModel)
class AppAdmin(admin.ModelAdmin):
    list_display = ['app_name', 'create_time', 'update_time', 'app_id', 'app_secret',
                    'token', 'bind']

    readonly_fields = ['app_id', 'app_secret', 'bind']

    def save_model(self, request, obj, form, change):
        """创建app"""
        result = super().save_model(request, obj, form, change)
        if change is False:
            app_id, app_secret = models.AppModel.create_app()
            obj.app_id = app_id
            obj.app_secret = app_secret
            obj.save()
        return result


@admin.register(models.ForwardMessageConfModel)
class ForwardMessageConfAdmin(admin.ModelAdmin):
    list_display = ['app', 'url']


@admin.register(models.WxUserModel)
class WxUserAdmin(admin.ModelAdmin):
    list_display = ['puid', 'name', 'avatar_url', 'nick_name', 'user_name', 'remark_name', 'signature', 'sex',
                    'province', 'city']

    readonly_fields = list_display + ['friends']

    def avatar_url(self, row):
        avatar = row.avatar
        if avatar:
            html = f'<img id="" src="/{avatar}" width=38>'
            return mark_safe(html)
        return avatar

    avatar_url.short_description = '头像'


@admin.register(models.WxGroupModel)
class WxGroupAdmin(admin.ModelAdmin):
    list_display = ['puid', 'name', 'avatar_url', 'nick_name', 'user_name', 'owner']
    readonly_fields = list_display

    def avatar_url(self, row):
        avatar = row.avatar
        if avatar:
            html = f'<img id="" src="/{avatar}" width=38>'
            return mark_safe(html)
        return avatar

    avatar_url.short_description = '头像'


@admin.register(models.MessageModel)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'type', 'create_time', 'receive_time', 'is_at', 'member', 'owner', '_sender', '_receiver']

    def _sender(self, row):
        return row.sender

    def _receiver(self, row):
        return row.receiver

    _sender.short_description = '发送人'
    _receiver.short_description = '接受人'

    readonly_fields = list_display


@admin.register(models.TextMessage)
class TextMessageAdmin(admin.ModelAdmin):
    list_display = ['message', 'text']


@admin.register(models.MapMessage)
class MapMessageAdmin(admin.ModelAdmin):
    list_display = ['scale', 'label', 'maptype', 'poiname', 'poiid', 'url', 'text', 'x', 'y']


@admin.register(models.PictureMessage)
class PictureMessageAdmin(admin.ModelAdmin):
    list_display = ['image_url', 'img_height', 'img_width']
    readonly_fields = list_display + ['message']

    def image_url(self, row):
        url = row.image
        if url:
            html = f'<img id="" src="/{url}" width=38>'
            return mark_safe(html)
        return url

    image_url.short_description = '图片'


@admin.register(models.CardMessage)
class CardMessageAdmin(admin.ModelAdmin):
    list_display = ['avatar_url', 'nickname', 'alias', 'province', 'city', 'sign', 'sex', 'username', ]

    def avatar_url(self, row):
        url = row.avatar
        if url:
            html = f'<img id="" src="{url}" width=38>'
            return mark_safe(html)
        return url

    avatar_url.short_description = '头像'
