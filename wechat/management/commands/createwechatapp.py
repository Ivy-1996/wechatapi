from django.core.management.base import BaseCommand
from wechat.models import AppModel


class Command(BaseCommand):

    def handle(self, *args, **options):
        app_name = input('please enter the name of wechat app:')
        token = input(f'please enter the token of {app_name} app:')
        app_id, app_secret = AppModel.create_app()
        AppModel.objects.create(app_name=app_name, app_id=app_id, app_secret=app_secret, token=token)
        self.stdout.write(f"""create app successfuly!\n  your app_id: {app_id}\n  your app_secret: {app_secret}""")




