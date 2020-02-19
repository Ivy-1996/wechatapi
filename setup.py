from distutils.core import setup

setup(name='wechat_api',
      version='0.3',
      description='wechat api for web',
      author='ivy',
      author_email='919624032@qq.com',
      url='https://github.com/Ivy-1996/wechatapi.git',
      packages=['wechat', 'wechat.core', 'wechat.management', 'wechat.migrations'],
      python_requires='>=3.6',
      install_requires=['djangorestframework', 'wxpy', 'django_redis', 'requests', 'django_filter']
      )
