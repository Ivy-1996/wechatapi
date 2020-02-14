from django_redis import get_redis_connection

from wechat import models
from wechat.core import pkl_path

from wxpy import Bot

from .const import ALIVE
from . import exception

import threading
import os
import time


def update_app_info(app_name):
    if app_name is not None:
        try:
            app = models.AppModel.objects.get(app_name=app_name)
            _update_single_app_info(app)
        except models.AppModel.DoesNotExist:
            print('app不存在!')
    else:
        apps = models.AppModel.objects.all()
        for app in apps:
            _update_single_app_info(app)


def _update_single_app_info(app):
    cache_path_name = f'{app.app_id}_cache.pkl'
    cache_path = os.path.join(pkl_path, cache_path_name)
    if not os.path.exists(cache_path):
        print(f'{cache_path_name}不存在!')
        return

    bot = Bot(cache_path=cache_path)

    bot.enable_puid(f'{app.app_id}.pkl')

    update_app(bot, app)


def update_app(bot, app):
    friends_update = threading.Thread(target=update_friends, args=(bot, app))
    groups_update = threading.Thread(target=update_groups, args=(bot,))
    mps_update = threading.Thread(target=update_mps, args=(bot,))

    friends_update.start()
    groups_update.start()
    mps_update.start()


def update_app_info_by_view(request):
    bot = get_cache_bot(request)
    update_app(bot, request.auth)


def update_friends(bot, app):
    """更新好友"""
    friends = bot.friends(update=True)
    for friend in friends:
        time.sleep(0.1)
        try:
            obj = models.WxUserModel.get_user(friend)
            # 添加到好友列表
            app.bind.friends.add(obj)
            print(f'{obj} 更新完毕~')
        except Exception as e:
            print(e.args)
            continue

    print(f'{bot.self.name}更新完毕~, 共更新了{len(friends)}个好友')


def update_groups(bot):
    """更新群"""
    groups = bot.groups(update=True)
    for group in groups:
        time.sleep(0.1)
        try:
            obj = models.WxGroupModel.get_group(group)
            # 更新群员列表
            update_members(group, obj)
            print(f'{obj} 更新完毕~')
        except Exception as e:
            print(e.args)
            continue

    print(f'{bot.self.name}更新完毕~, 共更新了{len(groups)}个群')


def update_mps(bot):
    """更新公众号"""
    mps = bot.mps(update=True)
    for mp in mps:
        time.sleep(0.1)
        try:
            obj = models.WxMpsModel.get_mp(mp)
            print(f'{obj} 更新完毕~')
        except Exception as e:
            print(e.args)
            continue

    print(f'{bot.self.name}更新完毕~, 共更新了{len(mps)}个公众号')


def update_members(group, obj: models.WxGroupModel):
    """更新群员"""
    members = group.members
    for member in members:
        user = models.WxUserModel.get_user(member)
        obj.members.add(user)


def get_cache_path(request):
    return os.path.join(pkl_path, f'{request.auth.app_id}_cache.pkl')


def get_alive_key(request):
    return f'{request.auth.app_id}_alive'


def get_puid_path(request):
    return f'{request.auth.app_id}.pkl'


def get_bot_alive(request):
    coon = get_redis_connection('default')
    alive_key = get_alive_key(request)
    alive = coon.get(alive_key)
    if alive is not None:
        alive = int(alive)
        return alive


def get_cache_bot(request):
    alive = get_bot_alive(request)
    assert alive == ALIVE, '微信号不在线!无法使用缓存登陆'

    cache_path = get_cache_path(request)
    bot = Bot(cache_path=cache_path)
    puid_path = get_puid_path(request)
    bot.enable_puid(puid_path)
    return bot


def get_message_receiver(bot: Bot, puid: str):
    receiver = bot.search(puid=puid)
    if not receiver:
        raise exception.PUIDSearchError()
    return receiver[0]


def send_message(bot: Bot, puid, msg_type, text, file_path):
    receiver = get_message_receiver(bot, puid)
    if msg_type == 'text':
        return receiver.send_msg(text)
    elif msg_type == 'image':
        return receiver.send_image(file_path)
    elif msg_type == 'video':
        return receiver.send_video(file_path)
    elif msg_type == 'file':
        return receiver.send_file(file_path)
    else:
        raise exception.SendMessageNotAllowedException()
