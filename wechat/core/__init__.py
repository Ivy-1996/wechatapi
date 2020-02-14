from django.conf import settings
import os

default_pkls_path = os.path.join(settings.BASE_DIR, 'pkls')

PKLS_PATH = getattr(settings, 'PKLS_PATH', None)

if PKLS_PATH is None and not os.path.exists(default_pkls_path):
    os.makedirs(default_pkls_path)

pkl_path = PKLS_PATH or default_pkls_path

Headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36'
}
