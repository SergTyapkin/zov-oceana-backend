import hashlib
from flask import jsonify, make_response, current_app
from flask_mail import Mail, Message

from src.constants import HTTP_OK


def hash_sha256(auth_string: str) -> str:
    return hashlib.sha256(auth_string.encode('utf-8')).hexdigest()


def jsonResponse(resp: dict | str, code: int = HTTP_OK):
    if isinstance(resp, str):
        resp = {"info": resp}

    return make_response(jsonify(resp), code)


def send_email(email, title, htmlBody):
    with current_app.app_context():
        mail = Mail()
        msg = Message(
            title, 
            recipients=[email],
            sender=(current_app.config['MAIL_DEFAULT_SENDER'], current_app.config['MAIL_DEFAULT_SENDER'])
        )
        msg.html = htmlBody
        mail.send(msg)
