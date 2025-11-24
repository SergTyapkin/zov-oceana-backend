from dataclasses import dataclass
from threading import Thread
import json

import telebot

from src.connections import config
from src.database.databaseUtils import createSecretCode


@dataclass
class TgBotMessageTexts:
    registrationGotten = "ℹ️ Вы зарегистрировались на мероприятие \"%s\".\n\nОжидайте подтверждения вашей регистрации"
    registrationCanceled = "ℹ️ Ваша регистрация на мероприятие \"%s\" отменена"
    registrationConfirmed = "✅ Ваша регистрация на мероприятие \"%s\" принята!\n\nПриходите на фестиваль в составе маршалов"
    registrationRejected = "❌ Ваша регистрация на мероприятие \"%s\" отклонена\n\nК сожалению вы не сможете быть в составе маршалов в этот раз :("


class TgBotClass:
    def __new__(cls, config):
        if not hasattr(cls, 'instance'):
            cls.token = config['tg_bot_token']
            cls.is_enabled = config['tg_bot_enabled']
            cls.thread = None
            cls.init(cls)
            cls.instance = super(TgBotClass, cls).__new__(cls)
        return cls.instance

    def init(self):
        if not self.is_enabled:
            print("TgBot not enabled in config")
            return

        try:
            self.bot = telebot.TeleBot(self.token)

            markupWithLinkButton = telebot.types.InlineKeyboardMarkup()
            btn1 = telebot.types.InlineKeyboardButton(
                text='Перейти на сайт',
                url='https://zovoceana.ru'
            )
            markupWithLinkButton.add(btn1)

            # errors handling decorator
            def errorsHandling(foo):
                def handleErrors(message):
                    try:
                        return foo(message)
                    except Exception as e:
                        print("[TgBot] Internal error when handling:", e)
                        try:
                            self.bot.send_message(
                                message.from_user.id,
                                f"❗❗❗ Внутренняя ошибка сервера при обработке сообщения: {e} ❗❗❗",
                            )
                        except Exception as e:
                            print("[TgBot] Cannot send error message to client!", e)
                        return
                return handleErrors

            @self.bot.message_handler(commands=['start'])
            @errorsHandling
            def startHandler(message):
                deepLinkText = message.text.split()[1] if len(message.text.split()) > 1 else None
                print(f"TgBot get start command from #{message.from_user.id}, text: \"{message.text}\". Response with default text")
                if deepLinkText == 'auth_by_code':  # Generate enter by code auth link
                    secretCode = createSecretCode(message.from_user.id, "auth", json.dumps({
                        'id': message.from_user.id,
                        'first_name': message.from_user.first_name,
                        'last_name': message.from_user.last_name,
                        'username': message.from_user.username,
                    }))
                    print(f"TgBot generates auth by code. Code = {secretCode}")
                    markup = telebot.types.InlineKeyboardMarkup()
                    btnEnter = telebot.types.InlineKeyboardButton(
                        text='Войти на сайте',
                        url=f'https://zovoceana.ru/login?code={secretCode}'
                    )
                    markup.add(btnEnter)
                    self.bot.send_message(
                        message.from_user.id,
                        "🔒 Нажмите на кнопку ниже для входа в профиль\n<i>Кнопка одноразовая и работает ровно час</i>",
                        parse_mode='html',
                        reply_markup=markup
                    )
                else:
                    self.bot.send_message(
                        message.from_user.id,
                        "📝 Этот бот будет присылать уведомления о действиях и заказах на сайте zovoceana.ru",
                        reply_markup=markupWithLinkButton
                    )

            @self.bot.message_handler()
            @errorsHandling
            def anyMessageHandler(message):
                print(f"TgBot get message from #{message.from_user.id}:", message.text, ". Response with default text")
                self.bot.send_message(
                    message.from_user.id,
                    "❗ Бот не принимает сообщения, а только уведомляет о действиях и заказах на сайте",
                    reply_markup=markupWithLinkButton
                )

            print("[TgBot] successfully initialized")
        except:
            print("[TgBot] Cannot connect to Telegram Bot.")

        self.thread = Thread(target=self.startBotPolling, args=[self], daemon=True)
        self.thread.start()

    def sendMessage(self, userTgId: str, MessageText: str, *values: list[str]):
        if not self.is_enabled:
            print("[TgBot] TgBot not enabled in config")
            return
        message = MessageText % values
        print(f"[TgBot] send message to #{userTgId}:", message)
        self.bot.send_message(userTgId, message)

    def startBotPolling(self):
        if not self.is_enabled:
            return
        try:
            self.bot.polling(none_stop=True, interval=0)
        except Exception as e:
            print(f"[TgBot] Error in polling cycle:", e)


TgBot = TgBotClass(config)
