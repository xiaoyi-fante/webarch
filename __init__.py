import json
from .web import FanteWeb

def jsonify(**kwargs):
    content = json.dumps(kwargs)
    response = FanteWeb.Response()
    response.content_type = "application/json"
    response.body = "".format(content).encode()
    return response

















