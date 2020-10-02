from wsgiref.simple_server import make_server
from webarch import FanteWeb, jsonify

idx = FanteWeb.Router()
py = FanteWeb.Router('/python')

FanteWeb.register(idx)
FanteWeb.register(py)

@idx.get('^/$')
def index(request:FanteWeb.Request):
    print(request)
    res = FanteWeb.Response()
    res.body = "<h1>爱学习的fante</h1>".encode()
    return res

@py.get('/{name:str}/{id:int}')
def index(request:FanteWeb.Request):
    res = FanteWeb.Response()
    res.body = "<h1>爱学习的fante写Python {}</h1>".format(request.vars.id).encode()
    return res

# 定义一个拦截器
@idx.reg_postinterceptor
def showjson(ctx, request, response):
    body = response.body.decode()
    return jsonify(body=body)

if __name__ == "__main__":
    ip = "127.0.0.1"
    port = 9999
    server = make_server(ip, port, FanteWeb())

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
