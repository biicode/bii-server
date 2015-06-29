from bottle import request


def get_user_ip():
    if 'HTTP_X_FORWARDED_FOR' in request:
        # on heroku, there is a proxy
        ip_adds = request.get('HTTP_X_FORWARDED_FOR').split(",")
        ip = ip_adds[0]
    else:
        ip = request.environ.get('REMOTE_ADDR')
    return ip
