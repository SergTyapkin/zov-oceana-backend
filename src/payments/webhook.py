from flask import Request

from src.payments.polling import stopPolling
from src.payments.types import PaymentResponse
from src.payments.utils import generateToken


def paymentsWebhook(request: Request, onPaymentStatusChanged):
    try:
        req = request.json
        paymentId = req['PaymentId']
        orderId = req['OrderId']
        status = req['Status']
        token = req['Token']
    except Exception as err:
        raise TypeError(f"Не удалось сериализовать json: {str(err)}")
    
    # 1. Проверяем токен
    myToken = generateToken(req)
    if myToken != token:
        print("ОШИБКА ВЕБХУКА: ТОКЕНЫ В ВЕБХУКЕ НЕ СОВПАДАЮТ")
        raise TypeError(f"Токен не прошёл проверку")

    payment = PaymentResponse(request)

    # 2. Завершаем потоки поллинга, если таковые были и ждали именно этот статус
    stopPolling(payment.orderId, payment.status)

    # 3. Вызываем коллбэк, что всё ок, можно обрабатывать
    onPaymentStatusChanged(payment)
