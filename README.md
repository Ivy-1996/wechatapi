## Django Wechat Api

`djangowechatapi`是基于`wxpy`和`django`制作的web应用

#### 安装

*	使用`pip`
    ```shell
    pip install djangowechatapi
    ```

*   源码安装
    ```shell
    git clone https://github.com/Ivy-1996/wechatapi.git
    
    cd wechatapi
    
    python setup.py install
    ```


#### 配置

* 该模块依赖`djangorestframework`和`django_filter`,需要把他们一起注册到`INSTALLED_APPS`里

* ```python
  INSTALLED_APPS = [
      'django.contrib.admin',
      'django.contrib.auth',
      'django.contrib.contenttypes',
      'django.contrib.sessions',
      'django.contrib.messages',
      'django.contrib.staticfiles',
      'rest_framework',
      'django_filters',
      'wechat',
  ]
  ```

* 添加到urls
* ```python
		urlpatterns = [
            path('admin/', admin.site.urls),
            path('', include('wechat.url'))
        ]
   ```

* 配置缓存

* ```python
  CACHES = {
      "default": {
          "BACKEND": "django_redis.cache.RedisCache",
          "LOCATION": f'redis://127.0.0.1/8',
          "OPTIONS": {
              "CLIENT_CLASS": "django_redis.client.DefaultClient",
          }
      }
  }
  ```

* 如果使用`django`默认的文件存储机制,需要在`SETTINGS`里面指定

* ```python
  MEDIA_PATH = os.path.join(BASE_DIR, 'media')
  ```

* 如果使用的是`mysql`数据库存储,则需要制定数据库和表的编码为`utf8mb4`

* 执行迁移脚本
   ```shell  
   python manager.py migrate
   ```


### 应用接口详情
*	由于网页版微信的保密机制,无法捕捉到用户的唯一id，这里采用的是wxpy提供的puid作为用户的唯一身份标识。

*	创建微信应用:
	*	命令行创建
		```shell
		python manager.py createwechatapp

		please enter the name of wechat app:<你的应用名>
		please enter the token of <你的应用名> app:<应用的token>
		create app successfuly!
		  your app_id: <app_id>
		  your app_secret: <app_secret>
		```
	*	或者通过网页使用django-admin创建

*	获取`access_token`
	*	所有api的默认的认证方式都是通过`access_token`来实现的，`access_token`的有效期为2个小时(可以在settings.py里面设置`ACCESS_TOKEN_EXPIRE_IN`来修改默认的2个小时)
	*	如果你觉得`access_token`不够安全,你也可以使用模块提供的`SignatureAuthentication`来实现实时用户认证。具体使用请参考源码。
	* 获取`access_token`(`access_token`依赖redis缓存,请确保上述配置均已配置完成)
	
		`method`：`GET`
		`url`: `/access_token?app_id=<app_id>&app_secret=<app_secret>`
		
		正常情况下,会返回
		```python
		{
			"access_token": "ACCESS_TOKEN",
			"expire_in": 7200
		}
		```
		如果出错了
		```python
		{
			"errmsg": [
				"无效的app"
			]
		}
		```
		
	
*	网页登陆
	`method`: `GET`
	`url`: `/login?access_token=<access_token>`
	`return`:
		```json
            {
                "uuid": "wbQeNse67Q==",
                "status": "0",
                "qrcode": "https://login.weixin.qq.com/qrcode/wbQeNse67Q=="
            }
		```
		参数说明
		`uuid`: 登陆二维码的唯一标识
		`status`: 登陆状态
		`qrcode`: 获取登陆二维码的地址

*	登陆验证
	`method`: `GET`
	`url`：`/check-login?access_token=<access_token>&uuid=<uuid>`
	`return`:
   
    ```json
    {
        "status": "408",
        "alive": null,
        "avatar": null
    }
	 ```
	
	`status`: 
		*	408:等待扫描登录
		*	201：已扫描，但为点击确认登录(此时可以获取到用户的头像)
		*	200：已扫描登录成功。
	`avatar`: 扫描用户的头像
`alive`: 登录后为True,退出登录后为False,未登录为null
	
	如果是做成网页版登录,前端在拿到登录二维码之后可以轮询这个接口来判断用户的登录状况
	
*	获取好友列表
	`method`: `GET`
	`url`: `/friends?access_token=<access_token>`
	`return`:
    ```json
    {
        "count": 140,
        "next": "http://127.0.0.1:8000/friends?access_token=fc99fe6e-7771-4e22-b89d-e9827463bf65&page=4",
        "previous": "http://127.0.0.1:8000/friends?access_token=fc99fe6e-7771-4e22-b89d-e9827463bf65&page=2",
        "results": [
            {
                "puid": "3b1b58a2",
                "name": "多吃点苹果🍏",
                "nick_name": "多吃点苹果🍏",
                "user_name": "@b3f13831c3eb3d51a2ce48c8d53da8bb1490426608de785d248d94783b1b58a2",
                "remark_name": "",
                "avatar": "http://127.0.0.1:8000/media/avatar/users/2020/02/12/3b1b58a2.jpg",
                "signature": "",
                "sex": 1,
                "province": "",
                "city": ""
            }，
        ......
        ]
    }
    ```
	`query_params`: `['puid', 'name', 'nick_name', 'user_name', 'remark_name', 'signature', 'sex','province', 'city']`

*	获取群组列表
	`method`: `GET`
	`url`: `groups?access_token=<access_token>`
	`return`: 
   
    ```json
    {
        "count": 15,
        "next": "http://127.0.0.1:8000/groups?access_token=fc99fe6e-7771-4e22-b89d-e9827463bf65&page=2",
        "previous": null,
        "results": [
        {
            "puid": "c17c31b9",
            "name": "浪里小白龙",
            "nick_name": "浪里小白龙",
            "user_name": "@@9976dba79a0deeab665a39b86dca838815ab2772d93ab377fd023bc2c17c31b9",
            "avatar": "http://127.0.0.1:8000/media/avatar/groups/2020/02/12/c17c31b9.jpg",
            "owner": "3b1b58a2"
        },
    ......
    ]
    }
	 ```
`query_params`: `['puid', 'name', 'nick_name', 'user_name', ]`
	
*	查看群成员列表
	`method`: `GET`
	`URL`: `/members/<group_puid>?access_token=<access_token>`
	`return`:
    ```json
        {
            "count": 4,
            "next": null,
            "previous": null,
            "results": [
            {
                "puid": "3b1b58a2",
                "name": "多吃点苹果🍏",
                "nick_name": "多吃点苹果🍏",
                "user_name": "@b3f13831c3eb3d51a2ce48c8d53da8bb1490426608de785d248d94783b1b58a2",
                "remark_name": "",
                "avatar": "http://127.0.0.1:8000/members/media/avatar/users/2020/02/12/3b1b58a2.jpg",
                "signature": "",
                "sex": 1,
                "province": "",
                "city": ""
            },
        ......
        ]
        }
    ```
	
*	微信公众号查询接口
	`method`: 'GET',
	`url`: '/mps?access_token=<access_token>'
	`return`: 
    ```json
    {
        "count": 126,
        "next": "http://127.0.0.1:8000/mps?access_token=fc99fe6e-7771-4e22-b89d-e9827463bf65&page=2",
        "previous": null,
        "results": [
        {
            "puid": "0e30af4a",
            "name": "进击的Coder",
            "nick_name": "进击的Coder",
            "province": "山东",
            "city": "济南",
            "signature": "分享技术文章和编程经验，内容多为网络爬虫、机器学习、Web 开发等方向。"
        },
        ......
        ]
        }
    ```
	`query_params`: `['puid', 'name', 'nick_name', 'province', 'city', 'signature']`
	
*	聊天记录查询(只会记录登录该站点后所收发的信息)
	`method`: `GET`
	`URL`: `/messages?access_token=<access_token>`
	`return`: 
    ```json
    {
        "count": 205,
        "next": "http://127.0.0.1:8000/messages?access_token=fc99fe6e-7771-4e22-b89d-e9827463bf65&page=2&puid=",
        "previous": null,
        "results": [
        {
            "id": 6920281997121075000,
                "content": {
                "message": 6920281997121075000,
            "text": "测试"
            },
            "type": {
                "sender": "wxusermodel",
                "receiver": "wxgroupmodel"
            },
            "create_time": "2020-02-12T10:01:24",
            "receive_time": "2020-02-12T10:01:24.231054",
            "is_at": false,
            "sender_puid": "3b1b58a2",
            "receiver_puid": "c9bc8647",
            "member": "3b1b58a2"
        },
        ......
        ]
    }
    ```
	`query_params`: `['type', 'create_time', 'receive_time', 'is_at', 'sender_puid', 'receiver_puid']`
	`参数说明`:
	 	`content`: 具体的聊天记录 
	 	`type`:  发送者和接受者的类型编码 {`wxusermodel`: `对象为好友`，`wxgroupmodel`: `对象为群`， `wxmpsmodel`: `对象为公众号`}
	 	`sender_puid&receiver_puid`: 发送者和接受者的唯一身份标识，具体请参考`type`字段
	 	`member`: 群成员.当该条消息来自群的时候,这个字段才会有值，参考该条信息，该member对象为sender发送者
   	 
  
	​	


*	主动发送消息
	`method`: `post`
	`url`: `send-message?access_token=<access_token>`
	`params`: 
	
	 | 字段        | 必填参数 |  类型  | desc|
   	 | --------   | --------:| :----:  | :----:|
   	 | type       |    是    |   string| 发送消息的类型(text, image,file, video)  |
   	 | puid       |    是    |   string |消息接收对象的唯一身份标识,puid可以为好友,群组,公众号等任意一种。该参数为必填参数|
   	 | text       |    否    |  string  |发送的文本内容,当type为text时,该参数必填 |
   	 | file       |    否    |  File    |文件对象。当type为'image', 'video', 'file'中的一种时,file为必填参数 |
	
	`return`:
    ```json
    {
        "id": 6920281997121075000,
        "content": {
            "message": 6920281997121075000,
            "text": "测试"
        },
        "type": {
            "sender": "wxusermodel",
            "receiver": "wxgroupmodel"
        },
        "create_time": "2020-02-12T10:01:24",
        "receive_time": "2020-02-12T10:01:24.231054",
        "is_at": false,
        "sender_puid": "3b1b58a2",
        "receiver_puid": "c9bc8647",
        "member": "3b1b58a2"
    }
    ```

*	主动更新列表
	*	更新好友列表,群组列表，公众号列表
	`method`: `get`
	`url`: `update?access_token=<access_token>`
	`return`: `{'msg': '更新成功!'}`
	

#### 自定义

*	微信号登陆之后，模块默认的行为为保存消息，有时候我们需要定制一些功能,这就需要修改登陆后的默认行为了

```python
from wechat.views import LoginView
from wechat.core.bot import DefaultBot
from wechat.core.handles import BaseHandle


###### views.py

class FirstHandle(BaseHandle):

    def text(self):
        print(self.message)


class SecondHandle(BaseHandle):

    def default_handle(self, **kwargs):
        print(self.message)


class MyBot(DefaultBot):
    handler_classes = [FirstHandle, SecondHandle]


class MyLoginView(LoginView):
    bot_class = MyBot


#######  urls.py
from django.urls import path

urlpatterns = [
    path('my_login', MyLoginView.as_view(), name='my_login')
]
```



*	自定义的登录视图需要继承`wechat.LoginView`,并且需要制定`bot_class`
*	自定义的`bot_class`需要继承默认的`DefaultBot`,并且需要制定定义消息处理的handle类列表`handler_classes`, 或者你可以重写`get_handler_classes`类方法。handler_classes里的每个handle类都会接收到消息。
*	自定义的handle_class需要继承`BaseHandle`，想要处理不同的消息类型，只要在Handle_class里写上消息类型的小写的方法即可,如，想在一个Handle_class里面处理消息类型为`Text`的请求，如上`FirstHandle`即可。如果没有定义消息类型的方法，那么默认该条消息不会被处理,你也可以如上`SecondHandle`来修改默认行为。一个handle可以响应多种消息类型。

#### 常见的http状态码
	200：访问成功
	201：执行成功
	400：客户端错误
	401：用户未认证
	403：禁止
	404：资源不存在

#### 命令行模式

* 创建wechat应用

  ```shell
  python manager.py createwechatapp
  ```

* 更新app绑定用户的列表详情(如上述`update`接口)

  ```shell
  python manager.py update_bot  <app_name>
  ```

  