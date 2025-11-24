from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart

import smtplib
from email.mime.text import MIMEText
from datetime import datetime

from src.connections import config

DB_NAME = "tech-support"
MAIL_RECIPIENT = config["mail_address"]
MAIL_HTML = """<html>
  <head></head>
  <body>
    <h1>Ура, новый бэкап базы данных!</h1>
  </body>
</html>"""

if __name__ == '__main__':
    # os.system(MAKE_BACKUP_CMD)  # make backup

    WEEKDAY = datetime.today().strftime('%A')
    TIMESTAMP = datetime.today().strftime('%d.%m.%Y-%H:%M:%S')
    PG_DUMP_FILENAME = f"backup_{WEEKDAY}.sql.backup"
    PG_DUMP_FULLPATH = f"./pg_backups/{PG_DUMP_FILENAME}"
    MAIL_FILE_NAME = f"backup_{WEEKDAY}_{TIMESTAMP}.pg_backup"

    msg = MIMEMultipart()
    msg['Subject'] = f"{WEEKDAY}(GMT) Backup of {DB_NAME}"
    msg['From'] = config["mail_sender_name"]
    msg['To'] = MAIL_RECIPIENT
    msg.attach(MIMEText(MAIL_HTML, 'html'))
    with open(PG_DUMP_FULLPATH, "rb") as f:
        part = MIMEApplication(
            f.read(),
            Name=MAIL_FILE_NAME
        )
    # After the file is closed
    part['Content-Disposition'] = f'attachment; filename="{MAIL_FILE_NAME}"'
    msg.attach(part)

    server = smtplib.SMTP(host=config["SMTP_mail_server_host"], port=config["SMTP_mail_server_port"])
    server.set_debuglevel(1)
    server.ehlo()
    server.starttls()
    server.login(config["mail_address"], config["mail_password"])
    server.send_message(msg)
    server.quit()
    print(f'Successfully sent the mail with backup to: {MAIL_RECIPIENT} as {MAIL_FILE_NAME}')
