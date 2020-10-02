from webob import Response, Request, dec, exc

import re

class DictObj:
    def __init__(self, d:dict):
        if isinstance(d, (dict,)):
            self.__dict__['_dict'] = d
        else:
            self.__dict__['_dict'] = {}
    def __getattr__(self, item):
        try:
            return self._dict[item]
        except KeyError:
            raise AttributeError("Attribute {} not Found".format(item))

class Context(dict):
    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError("Attribute {} not Found".format(item))

    def __setattr__(self, key, value):
        self[key] = value

class NestedContext(Context):
    def __init__(self, globalcontext: Context = None):
        super().__init__()
        self.globalcontext = globalcontext

    def relate(self, globalcontext: Context = None):
        self.globalcontext = globalcontext

    def __getattr__(self, item):
        if item in self.keys():
            return self[item]
        return self.globalcontext[item]

class _Router:
    KVPATTERN = re.compile('/({[^{}:]+:?[^{}:]*})')

    TYPEPATTERNS = {
        'str': r'[^/]+',
        'word': r'\w+',
        'int': r'[+-]?\d+',
        'float': r'[+-]?\d+\.\d+', # 严苛的要求必须是15.6这样的形式
        'any': r'.+'
    }

    TYPECAST = {
        'str': str,
        'word': str,
        'int': int,
        'float': float,
        'any': str
    }

    # /python/class
    def transform(self, kv: str):
        name, _, type = kv.strip('/{}').partition(':')
        return '/(?P<{}>{})'.format(name, self.TYPEPATTERNS.get(type, '\w+')), name, self.TYPECAST.get(type, str)

    def parse(self, src: str):
        start = 0
        res = ''
        translator = {}
        while True:
            matcher = self.KVPATTERN.search(src, start)
            if matcher:
                res += matcher.string[start:matcher.start()]
                tmp = self.transform(matcher.string[matcher.start():matcher.end()])
                res += tmp[0]
                translator[tmp[1]] = tmp[2]
                start = matcher.end()
            else:
                break
        # 没有任何匹配应该原样返回字符串
        if res:
            return res, translator
        else:
            return src, translator

    def __init__(self, prefix:str=''):
        self.__prefix = prefix.rstrip('/\\')
        self.__routetable = []

        self.ctx = NestedContext() # 未绑定全局的上下文

        # 拦截器
        self.preinterceptor = []
        self.postinterceptor = []

    def reg_preinterceptor(self, fn):
        self.preinterceptor.append(fn)
        return fn

    def reg_postinterceptor(self, fn):
        self.postinterceptor.append(fn)
        return fn

    @property
    def prefix(self):
        return self.__prefix

    def route(self, rule, *methods):
        def wrapper(handler):
            pattern, translator = self.parse(rule)
            self.__routetable.append((methods, re.compile(pattern), translator, handler))
            return handler
        return wrapper

    def get(self, pattern):
        return self.route(pattern, 'GET')

    def post(self, pattern):
        return self.route(pattern, 'POST')

    def head(self, pattern):
        return self.route(pattern, 'HEAD')

    def match(self, request:Request) -> Response:
        # 属于Router实例管的prefix
        if not request.path.startswith(self.prefix):
            return

        for fn in self.preinterceptor:
            request = fn(self.ctx, request)

        for methods, pattern, translator, handler in self.__routetable:
            if not methods or request.method.upper() in methods:
                matcher = pattern.match(request.path.replace(self.prefix, "", 1))
                if matcher:
                    newdict = {}
                    for k,v in matcher.groupdict().items():
                        newdict[k] = translator[k](v)
                    request.vars = DictObj(newdict)

                    response = handler(request)

                    for fn in self.postinterceptor:
                        response = fn(self.ctx, request, response)

                    return response

class FanteWeb:
    # 这种是特别常用的一种方式，这样就定义了只有一个访问入口为FanteWeb，其他的类作为FanteWeb的类属性被其他模块调用
    Router = _Router
    Request = Request
    Response = Response

    ctx = Context()
    def __init__(self, **kwargs):
        self.ctx.app = self
        for k,v in kwargs.items():
            self.ctx[k] = v

    ROUTERS = []

    PREINTERCEPTOR = []
    POSTINTERCEPTOR = []

    @classmethod
    def reg_preinterceptor(cls, fn):
        cls.PREINTERCEPTOR.append(fn)
        return fn

    @classmethod
    def reg_postinterceptor(cls, fn):
        cls.POSTINTERCEPTOR.append(fn)
        return fn

    @classmethod
    def register(cls, router:Router):
        router.ctx.relate(cls.ctx)
        router.ctx.router = router
        cls.ROUTERS.append(router)
        return router

    @dec.wsgify
    def __call__(self, request:Request) -> Response:
        for fn in self.PREINTERCEPTOR:
            request = fn(self.ctx, request)

        for router in self.ROUTERS:
            response = router.match(request)

            if response:
                for fn in self.POSTINTERCEPTOR:
                    response = fn(self.ctx, request, response)
                return response
        raise exc.HTTPNotFound("您访问的页面被外星人劫持了")
