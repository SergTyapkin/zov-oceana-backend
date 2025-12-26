from dataclasses import dataclass
from threading import Thread
import json

import telebot

from src.config import CONFIG
from src.constants import *
from src.database.databaseUtils import createSecretCode


@dataclass
class TgBotMessageTexts:
    orderCreated =   f"✅ Создан заказ №`%s`.\nВ заказе: %s"
    orderAccepted =  f"✅ Заказ №`%s` подтвержден и передан в сборку"
    orderPrepared =  f"✅ Заказ №`%s` собран и передан в доставку"
    orderPreparedWithCode =  f"✅ Заказ №`%s` собран и передан в доставку.\nКод отслеживания: `%s`"
    orderDelivered = f"✅ Заказ №`%s` доставлен"
    orderCancelled = f"❌ Заказ №`%s` был отменён"
    orderDeleted =   f"❌ Заказ №`%s` был удалён"
    
    orderPaymentAuthorized = f"✅ Деньги для оплаты заказа №`%s` заморожены на вашей карте.\nОператор позвонит вам и оплата будет списана после подтверждения заказа"
    orderPaymentConfirmed =  f"✅ Заказ №`%s` успешно оплачен"
    orderPaymentExpired =    f"❌ Заказ №`%s` не оплачен в течение {round(CONFIG.tbank.max_order_pay_time_sec / 60)} минут. _Пожалуйста, повторите попытку оплаты [на странице заказа]({CONFIG.deploy_full_url}/payment/order/%s)_"
    orderPaymentRejected =   f"❌ Оплата заказа №`%s` отклонена банком. _Пожалуйста, повторите попытку оплаты [на странице заказа]({CONFIG.deploy_full_url}/payment/order/%s)_"
    orderPaymentRefunded =   f"♻ Возврат по заказу №`%s` был успешно произведен.\n_Деньги возвращены на счет, с которого заказ был оплачен_"
    orderPaymentCancelled =  f"⚠ Оплата заказа №`%s` отменена.\n_Деньги на вашем счете, замороженные для оплаты этого заказа, разморожены_"
    
    orderStatusToCreated =   f"ℹ️ Статус заказа №`%s` изменен на 'создан, не подтвержден'"
    orderStatusToAccepted =  f"ℹ️ Статус заказа №`%s` изменен на 'подтвержден, ожидает сборки'"
    orderStatusToPrepared =  f"ℹ️ Статус заказа №`%s` изменен на 'собран, ожидает доставки'"
    orderStatusToDelivered = f"ℹ️ Статус заказа №`%s` изменен на 'доставлен'"
    orderStatusToCancelled = f"ℹ️ Статус заказа №`%s` изменен на 'отменён'"
    
    orderPaymentStatusToNew =        f"ℹ️ Статус оплаты заказа №`%s` изменен на 'Создана, не произведена'"
    orderPaymentStatusToAuthorized = f"ℹ️ Статус оплаты заказа №`%s` изменен на 'Деньги заморожены на карте, оплата не списана'"
    orderPaymentStatusToConfirmed =  f"ℹ️ Статус оплаты заказа №`%s` изменен на 'Успешно произведена'"
    orderPaymentStatusToExpired =    f"ℹ️ Статус оплаты заказа №`%s` изменен на 'Истек срок проведения платежа'"
    orderPaymentStatusToRejected =   f"ℹ️ Статус оплаты заказа №`%s` изменен на 'Отклонена банком'"
    orderPaymentStatusToRefunded =   f"ℹ️ Статус оплаты заказа №`%s` изменен на 'Произведен возврат'"
    orderPaymentStatusToCancelled =  f"ℹ️ Статус оплаты заказа №`%s` изменен на 'Отменена'"

class TgBotClass:
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.token = CONFIG.telegram.bot_token
            cls.is_enabled = CONFIG.telegram.bot_enabled
            cls.thread = None
            cls.init(cls)
            cls.instance = super(TgBotClass, cls).__new__(cls)
        return cls.instance

    def init(self):
        if not self.is_enabled:
            print("[TgBot] TgBot not enabled in config")
            return

        try:
            self.bot = telebot.TeleBot(self.token)

            markupWithLinkButton = telebot.types.InlineKeyboardMarkup()
            btn1 = telebot.types.InlineKeyboardButton(
                text='Перейти на сайт',
                url=CONFIG.deploy_full_url
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
                print(f"[TgBot] Got start command from #{message.from_user.id}, text: \"{message.text}\". Response with default text")
                if deepLinkText == 'auth_by_code':  # Generate enter by code auth link
                    secretCode = createSecretCode(message.from_user.id, "auth", json.dumps({
                        'id': message.from_user.id,
                        'first_name': message.from_user.first_name,
                        'last_name': message.from_user.last_name,
                        'username': message.from_user.username,
                    }))
                    print(f"[TgBot] generates auth by code. Code = {secretCode}")
                    markup = telebot.types.InlineKeyboardMarkup()
                    btnEnter = telebot.types.InlineKeyboardButton(
                        text='Войти на сайте',
                        url=f'{CONFIG.deploy_short_url}/login?code={secretCode}'
                    )
                    markup.add(btnEnter)
                    self.bot.send_message(
                        message.from_user.id,
                        "🔒 Нажмите на кнопку ниже для входа в профиль\n<i>Кнопка одноразовая и работает ровно час</i>",
                        parse_mode='HTML',
                        reply_markup=markup
                    )
                else:
                    self.bot.send_message(
                        message.from_user.id,
                        f"📝 Этот бот будет присылать уведомления о действиях и заказах на сайте {CONFIG.deploy_short_url}",
                        reply_markup=markupWithLinkButton
                    )

            @self.bot.message_handler()
            @errorsHandling
            def anyMessageHandler(message):
                print(f"[TgBot] Got message from #{message.from_user.id}:", message.text, ". Response with default text")
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
        try:
            if not self.is_enabled:
                print("[TgBot] TgBot not enabled in config")
                return
            message = MessageText % values
            print(f"[TgBot] Send message to #{userTgId}:", message)
            self.bot.send_message(userTgId, message, parse_mode='MarkdownV2')
        except Exception as e: 
            print("[TgBot] ERROR: Can't send message to user:", userTgId, "Message:", message, "Error:", e)
    
    def startBotPolling(self):
        if not self.is_enabled:
            return
        try:
            self.bot.polling(none_stop=True, interval=0)
        except Exception as e:
            print(f"[TgBot] Error in polling cycle:", e)


TgBot = TgBotClass()
