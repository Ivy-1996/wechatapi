from distutils.core import setup

setup(name='djangowechatapi',
      version='0.52',
      description='wechat api for web',
      author='ivy',
      author_email='919624032@qq.com',
      url='https://github.com/Ivy-1996/wechatapi',
      packages=['wechat', 'wechat.core', 'wechat.management', 'wechat.management.commands', 'wechat.migrations'],
      python_requires='>=3.6',
      license='Apache License',
      install_requires=[
          'djangorestframework==3.11.0',
          'wxpy',
          'django_redis',
          'requests',
          'django_filter',
          'pillow',
      ]
      )
