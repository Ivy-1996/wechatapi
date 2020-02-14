from django.core.management.base import BaseCommand
from wechat.core import pkl_path
from wechat import models

import os


class Command(BaseCommand):
    help = 'flush all details of wechat bot'

    def handle(self, *args, **options):
        os.remove(pkl_path)
        models.AppModel.objects.all().delete()
        print('flush successed')
