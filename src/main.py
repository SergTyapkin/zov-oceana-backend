import os
from flask import Flask
from flask import g, request
from flask_mail import Mail

from colors import red, blue, green, purple, cyan, yellow, light_gray
import datetime
import time
from rfc3339 import rfc3339

from src.config import CONFIG
from src.blueprints.user import app as user_app
from src.blueprints.sql import app as sql_app
from src.blueprints.goods import app as goods_app
from src.blueprints.categories import app as categories_app
from src.blueprints.image import app as image_app
from src.blueprints.addresses import app as addresses_app
from src.blueprints.orders import app as orders_app
from src.blueprints.carts import app as cart_app
from src.blueprints.partners import app as partners_app
from src.blueprints.globals import app as globals_app
from src.blueprints.payments import app as payments_app, DB
from src.constants import HTTP_NOT_FOUND, HTTP_INTERNAL_ERROR
from src.middleware import Middleware
from src.utils.utils import jsonResponse

from src.database.SQLRequests import globals as SQLGlobals


app = Flask(__name__)
app.config['DEBUG'] = CONFIG.debug
app.wsgi_app = Middleware(app.wsgi_app, url_prefix='/api', cors_origins=CONFIG.cors_origins)

app.register_blueprint(user_app, url_prefix='/user')
app.register_blueprint(sql_app, url_prefix='/sql')
app.register_blueprint(goods_app, url_prefix='/goods')
app.register_blueprint(categories_app, url_prefix='/categories')
app.register_blueprint(image_app, url_prefix='/image')
app.register_blueprint(addresses_app, url_prefix='/addresses')
app.register_blueprint(orders_app, url_prefix='/orders')
app.register_blueprint(cart_app, url_prefix='/cart')
app.register_blueprint(partners_app, url_prefix='/partner')
app.register_blueprint(globals_app, url_prefix='/globals')
app.register_blueprint(payments_app, url_prefix='/payments')

app.config['MAIL_SERVER'] = CONFIG.email.smtp_host
app.config['MAIL_PORT'] = CONFIG.email.smtp_port
app.config['MAIL_USE_TLS'] = CONFIG.email.smtp_use_tls
app.config['MAIL_USERNAME'] = CONFIG.email.address
app.config['MAIL_DEFAULT_SENDER'] = CONFIG.email.sender_name
app.config['MAIL_PASSWORD'] = CONFIG.email.password

mail = Mail(app)


@app.route('/')
def home():
    return "Это начальная страница API сайта, а не сам сайт. Выйди отсюда!"


@app.route('/health')
def health():
    return jsonResponse({'health': 'ok'})


@app.errorhandler(404)
def error404(err):
    print(err)
    return jsonResponse("404 страница не найдена", HTTP_NOT_FOUND)


@app.errorhandler(500)
def error500(err):
    print(err)
    return jsonResponse("500 внутренняя ошибка сервера", HTTP_INTERNAL_ERROR)


@app.before_request
def start_timer():
    g.start = time.time()

@app.after_request
def log_request(response):
    now = time.time()
    duration = round((now - g.start) * 1000, 2)
    dt = datetime.datetime.fromtimestamp(now)
    timestamp = rfc3339(dt, utc=True)

    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    host = request.host.split(':', 1)[0]
    args = dict(request.args)

    json = ''
    try:
        json = request.json
    except:
        pass

    responseText = response.get_data().decode()

    log_params = [
        (timestamp, purple),
        (request.method, blue),
        (request.path, blue),
        (response.status_code, yellow),
        (f'duration={duration}ms', green),
        (f'ip={ip}', red),
        (f'host={host}', red),
        (f'query={args}', blue),
        (f'body={json}', cyan),
        (f'RES_code={response.status_code}', light_gray),
        (f'RES_data={responseText[:CONFIG.max_log_data_length] + (f"... ({len(responseText)} symbols total)" if len(responseText) > CONFIG.max_log_data_length else "")}', light_gray),
        (f'\n', light_gray),
    ]

    request_id = request.headers.get('X-Request-ID')
    if request_id:
        log_params.append(('request_id', request_id, yellow))

    parts = []
    for value, color in log_params:
        part = value
        coloredPart = color(part)
        parts.append(coloredPart)
    line = " ".join(parts)

    app.logger.info(line)

    return response


if __name__ == '__main__':
    # Create global settings if it doesn't exist now
    if not DB.execute(SQLGlobals.selectGlobals):
        DB.execute(SQLGlobals.insertGlobals)

    # Run app
    app.run(host=CONFIG.host, port=CONFIG.port, debug=CONFIG.debug)
