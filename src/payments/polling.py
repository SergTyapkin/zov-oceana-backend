import math
import threading
import time

from src.config import CONFIG
from src.payments.types import OrderPollingThreadData, PaymentStatuses
from src.payments.requests import getPaymentState


__ordersPollingThreads: dict[str, OrderPollingThreadData] = {}

def startPollingForPayment(order, user, onPaymentDataChanged, onPaymentStatusChanged, awaitingForStatuses: list[PaymentStatuses] = None):
    stopPolling(order['id'])
        
    initialStatus = order['paymentstatus']
    
    def poll():
        # Проверяем флаг завершения
        if stop_flag.is_set():
            return False
        
        try:
            payment = getPaymentState(order['paymentid'])
        except Exception as err:
            print(f"Ошибка при поллинге статуса оплаты #{order['paymentid']} заказа #{order['id']}:", err);
            return False
        
        # Если поменялись Route или Source - сохраняем их в базе
        if order['paymentroute'] != payment.route or order['paymentsource'] != payment.source:
            onPaymentDataChanged(payment, order, user)
        
        # Если статус не поменялся - выходим
        if payment.status == initialStatus:
            return False
        
        # Если поменялся - проверяем что на один из ожидаемых
        if payment.status not in awaitingForStatuses and awaitingForStatuses is not None:
            print(f"Ошибка: При поллинге статуса оплаты #{order['paymentid']} заказа #{order['id']}, он изменился на {payment.status}, хотя ожидался один из:", awaitingForStatuses);
            return False
        
        # Если изменился на один из ожидаемых - обрабатываем изменение
        print(f"✅ Cтатус оплаты #{order['paymentid']} заказа #{order['id']} изменился на {payment.status}");
        onPaymentStatusChanged(payment, order, user)
        return True
    
    def startPollingCycle():
        attempts = 0
        maxAttemts = math.ceil(CONFIG.tbank.max_order_pay_time_sec / CONFIG.tbank.payments_polling_interval_sec)
        while attempts < maxAttemts:
            if stop_flag.is_set():
                print(f"⏹️ Поллинг для платежа #{order['paymentid']} заказа #{order['id']} принудительно остановлен")
                return
            
            if poll():  # Заканчиваем, если мы дождались смены статуса на один из нужных 
                return
            time.sleep(CONFIG.tbank.payments_polling_interval_sec)
            attempts += 1

    stop_flag = threading.Event()
    thread = threading.Thread(target=startPollingCycle, daemon=True)
    thread.start()
    # Сохраняем тред для возможности его отмены
    __ordersPollingThreads[order['id']] = OrderPollingThreadData(thread, awaitingForStatuses, stop_flag)
    print(f"♻🚀 Started polling for payment #{order['paymentid']} order #{order['id']}")


def stopPolling(orderId, onlyForStatus=None):
    # Если тред для этого заказа уже есть, убиваем его
    existingThread = __ordersPollingThreads.get(orderId)
    
    if existingThread is None: return
    if onlyForStatus is not None and (
        existingThread.awaitingForStatuses is not None and
        len(existingThread.awaitingForStatuses) != 0 and
        onlyForStatus not in existingThread.awaitingForStatuses
    ): return

    existingThread.stop_flag.set()  # Устанавливаем флаг остановки
    # existingThread.thread.join()  # Ждем завершения
    del __ordersPollingThreads[orderId]  # Удаляем из словаря