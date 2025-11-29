import datetime
import hashlib
import json
import os
from geoip2 import database

from flask import jsonify, make_response, current_app, request
from flask_mail import Mail, Message

from src.constants import HTTP_OK


def hash_sha256(auth_string: str) -> str:
    return hashlib.sha256(auth_string.encode()).hexdigest()

def str_between(string: (str, bytes), start: (str, bytes), end: (str, bytes), replace_to: (str, bytes) = None):
    end_idx = start_idx = string.find(start) + len(start)
    if isinstance(end, list):
        while end_idx < len(string) and string[end_idx] not in end:
            end_idx += 1
    else:
        end_idx = string.find(end)

    if replace_to is None:
        return string[start_idx: end_idx], start_idx, end_idx
    return string[:start_idx] + replace_to + string[end_idx:]


def read_config(filepath: str) -> dict:
    try:
        file = open(filepath, "r")
        config = json.load(file)
        file.close()

        config["debug"] = str(os.environ.get("DEBUG", config["debug"])).lower() == 'true'
        config["db_user"] = os.environ.get("DB_USER", config["db_user"])
        config["db_host"] = os.environ.get("DB_HOST", config["db_host"])
        config["db_port"] = os.environ.get("DB_PORT", config["db_port"])
        config["db_name"] = os.environ.get("DB_NAME", config["db_name"])
        config["db_password"] = os.environ.get("DB_PASSWORD", config["db_password"])
        config["mail_password"] = os.environ.get("MAIL_PASSWORD", config["mail_password"])
        config["tg_bot_token"] = os.environ.get("TG_BOT_TOKEN", config["tg_bot_token"])
        config["tg_bot_enabled"] = str(os.environ.get("TG_BOT_ENABLED", config["tg_bot_enabled"])).lower() == 'true'

        if config['save_images_to_db'] is False:
            if not os.path.isdir(config['save_images_folder']):
                print("Folder to saving images doesn't exists. Creating", config['save_images_folder'], '...')
                os.mkdir(config['save_images_folder'])

        print("Config loaded:\n", json.dumps(config, indent=4))

        return config
    except Exception as e:
        print("Can't open and serialize json:", filepath)
        print(e)
        exit()


def count_lines(filename, chunk_size=4096) -> int:
    with open(filename) as file:
        return sum(chunk.count('\n') for chunk in iter(lambda: file.read(chunk_size), ''))


def html_prettify(headers: list, body: list, multilines: bool = False, row_onclick=None) -> str:
    if multilines:
        value_foo = lambda val: str(val).replace('\n', '<br>')
    else:
        value_foo = lambda val: str(val)

    thead = "<thead>\n"
    tbody = "<tbody>\n"
    for header in headers:
        thead += "<tr>\n"
        tbody += "<th>" + header + "</th>"
    thead += "</tr>\n"

    for row in body:
        tbody += "<tr" + ((" onclick=" + row_onclick(row[0]) + " style=\"cursor: pointer\"") if row_onclick else "") + ">\n"
        for value in row:
            tbody += "<td>" + value_foo(value) + "</td>"
        tbody += "</tr>\n"
    thead += "</thead>\n"
    tbody += "</tbody>\n"

    return "<table>\n" + thead + tbody + "</table>"


def jsonResponse(resp: dict or str, code: int = HTTP_OK):
    if isinstance(resp, str):
        resp = {"info": resp}

    return make_response(jsonify(resp), code)


def send_email(email, title, htmlBody):
    with current_app.app_context():
        mail = Mail()
        msg = Message(title, recipients=[email],
                      sender=(current_app.config['MAIL_DEFAULT_SENDER'], current_app.config['MAIL_DEFAULT_SENDER']))
        msg.html = htmlBody
        mail.send(msg)
