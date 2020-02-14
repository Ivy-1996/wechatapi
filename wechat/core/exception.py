class WeChatException(Exception):
    pass


class LoginTimeOutException(WeChatException):
    pass


class AppDoesNotExistException(WeChatException):
    pass


class InvalidTokenException(WeChatException):
    pass


class ForwardUrlDoesNotExistException(WeChatException):
    pass


class ForwardFailError(WeChatException):
    pass


class PUIDSearchError(WeChatException):
    pass


class SendMessageNotAllowedException(WeChatException):
    pass
