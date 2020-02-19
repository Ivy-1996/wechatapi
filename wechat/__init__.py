from .__version__ import __version__, __url__, __author__, __author_email__, __license__, __description__

from .models import AppModel


def get_version():
    return __version__


def get_app_model():
    return AppModel
