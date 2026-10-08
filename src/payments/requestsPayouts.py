import json
import time
import requests
import urllib3

from src.payments.utils import sign_payout_request_rsa
from src.config import CONFIG
from src.payments.types import PaymentResponse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def __sendPayoutRequest(url, params) -> PaymentResponse:
    params['TerminalKey'] = CONFIG.tbank.payout_terminal_key

    params = sign_payout_request_rsa(params)

    try:
        response = requests.post(
            url,
            json=params,
            headers={'Content-Type': 'application/json'},
            timeout=30,
            verify=False,
        )

        try:
            print(f"<<< Payout Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        except json.JSONDecodeError:
            print(f"<<< Raw response: {response.text}")

        if response.status_code != 200:
            raise Exception(f"Ошибка HTTP: {response.status_code}")

        res = PaymentResponse(response)
        if not res.success:
            raise Exception(f"Ошибка Tinkoff Payout: {res.message}; {res.details} (Код: {res.errorCode})")

        return res
    except requests.exceptions.Timeout as err:
        raise Exception(f"Превышено время ожидания ответа от Tinkoff: {str(err)}")
    except requests.exceptions.RequestException as err:
        raise Exception(f"Ошибка запроса к Tinkoff: {str(err)}")
    except json.JSONDecodeError as err:
        raise Exception(f"Ошибка парсинга ответа Tinkoff: {str(err)}")


# =========== Payout / SBP Methods =============

def initPayoutSbp(userId: str, phoneNumber: str, sbpBankId: int, amount: int, details: str = None) -> PaymentResponse:
    """
    Инициирует выплату через СБП по номеру телефона.

    Args:
        orderId: Уникальный номер заказа в системе мерчанта (<= 36 символов)
        phoneNumber: Номер телефона получателя (9-15 цифр, без +)
        sbpMemberId: Идентификатор банка-получателя в СБП (например, 100000000004)
        amount: Сумма в копейках (минимум 100)
        data: Дополнительные параметры (PaymentPurposeDetails без пробелов (^[A-Za-zА-Яа-яЁё0-9!"#$^_`{|}~№]+$), codeVO, incomeTypeCode)
    Returns:
        PaymentResponse со статусом CHECKED (успех) или REJECTED (ошибка)
    """

    return __sendPayoutRequest(
        CONFIG.tbank.payout_sbp_init_url,
        {
            'OrderId': f'payout_{userId}_{time.ctime().replace(" ", "-")}',
            'PhoneNumber': ''.join(c for c in phoneNumber if c.isdigit()),
            'SbpMemberId': sbpBankId,
            'Amount': amount,
            **({'DATA': {
                'PaymentPurposeDetails': details,
            }} if details else {}),
        }
    )


def makePayoutSbp(paymentId: str) -> PaymentResponse:
    """
    Подтверждает выплату через СБП.

    ВАЖНО: вызывать только после того, как Init вернул статус CHECKED.
    На подтверждение даётся 180 секунд, иначе операция перейдёт в REJECTED.

    Args:
        paymentId: Идентификатор операции из ответа initPayoutSbp

    Returns:
        PaymentResponse со статусом COMPLETING (успех) или REJECTED (ошибка)
    """

    return __sendPayoutRequest(
        CONFIG.tbank.payout_sbp_payment_url, 
        {
            'PaymentId': paymentId,
        }
    )


def getPayoutSbpState(paymentId: str) -> PaymentResponse:
    """
    Возвращает текущий статус выплаты через СБП.

    Используется, если нотификация не пришла.
    Возможные финальные статусы: CHECKED, COMPLETED, REJECTED.

    Args:
        paymentId: Идентификатор операции

    Returns:
        PaymentResponse со статусом
    """
    return __sendPayoutRequest(
        CONFIG.tbank.payout_sbp_get_state_url, 
        {
            'PaymentId': paymentId,
        }
    )


def getSbpBanks() -> PaymentResponse:
    """
    Возвращает список участников СБП, принимающих переводы.

    Используется для получения SbpMemberId для конкретного банка получателя.

    Returns:
        PaymentResponse со списком Members
    """
    return __sendPayoutRequest(
        CONFIG.tbank.payout_sbp_get_members_url, 
        {}
    )