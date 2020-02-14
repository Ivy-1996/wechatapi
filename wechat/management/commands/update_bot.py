from django.core.management.base import BaseCommand

from wechat.core.utils import update_app_info


class Command(BaseCommand):
    help = 'update all wechat info'

    def handle(self, *args, **options):
        app_name = options.get('app_name')
        return update_app_info(app_name)

    def add_arguments(self, parser):
        parser.add_argument('app_name', type=str)
