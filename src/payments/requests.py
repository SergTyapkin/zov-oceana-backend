import json
import time
import requests
import urllib3

from src.config import CONFIG
from src.payments.utils import generateToken
from src.payments.types import PaymentResponse

# Отключаем предупреждения о сертификатах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def __sendPaymentRequest(url, params) -> PaymentResponse:
    params['TerminalKey'] = CONFIG.tbank.terminal_key
    
    params['Token'] = generateToken(params)
    
    try:
        # Отпрвляем POST запрос на заданный url с заданным телом
        response = requests.post(
            url,
            json=params,
            headers={'Content-Type': 'application/json'},
            timeout=30,
            verify=False,  # Отключаем проверку SSL сертификата
        )
        
        # Логируем ответ
        try:
            print(f"<<< Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        except json.JSONDecodeError:
            print(f"<<< Raw response: {response.text}")
        
        # Проверяем статус
        if response.status_code != 200:
            raise Exception(f"Ошибка HTTP: {response.status_code}")
        
        # Проверяем успешность
        res = PaymentResponse(response)
        if not res.success:
            raise Exception(f"Ошибка Tinkoff: {res.message}; {res.details} (Код: {res.errorCode})")
        
        # Если всё в порядке - возвращаем структуру с данными
        return res
    except requests.exceptions.Timeout as err:
        raise Exception(f"Превышено время ожидания ответа от Tinkoff: {str(err)}")
    except requests.exceptions.RequestException as err:
        raise Exception(f"Ошибка запроса к Tinkoff: {str(err)}")
    except json.JSONDecodeError as err:
        raise Exception(f"Ошибка парсинга ответа Tinkoff: {str(err)}")


# =========== Requests =============
def getPaymentState(paymentId) -> PaymentResponse:    
    return __sendPaymentRequest(
        CONFIG.tbank.get_state_url, 
        {
            'PaymentId': paymentId,
        },
    )

def getPaymentQRHref(paymentId) -> PaymentResponse:    
    return __sendPaymentRequest(
        CONFIG.tbank.get_qr_url,
        {
            'PaymentId': paymentId,
            'DataType': 'PAYLOAD',  # или "IMAGE" для SVG
        },
    )

def cancelPayment(paymentId, amount=None) -> PaymentResponse:    
    return __sendPaymentRequest(
        CONFIG.tbank.cancel_url, 
        {
            'PaymentId': paymentId,
            **({'Amount': amount} if amount is not None else {}),
        }
    )

def confirmPayment(paymentId, orderData, amount=None) -> PaymentResponse:    
    return __sendPaymentRequest(
        CONFIG.tbank.confirm_url, 
        {
            'PaymentId': paymentId,
            **({'Amount': amount} if amount is not None else {}),
            **({'Route': orderData['paymentroute']} if orderData['paymentroute'] is not None else {}),
            **({'Source': orderData['paymentsource']} if orderData['paymentsource'] is not None else {}),
        }
    )

def initPayment(totalCost, orderData, userData, goods) -> PaymentResponse:    
    return __sendPaymentRequest(
        CONFIG.tbank.init_url, 
        {
            'Amount': round(totalCost),
            'OrderId': f'{orderData['id']}_{time.ctime().replace(" ", "-")}', # Добвляем к id заказа текущее время после _. В ответах от тинькоффа мы отрезаем время и получаем чистое id
            'Description': f"Оплата заказа №{orderData['number']} на сайте {CONFIG.deploy_short_url}",
            'CustomerKey': str(userData['id']),
            'Language': 'ru',
            'PayType': 'T' if CONFIG.tbank.use_two_stage_payments else 'O',  # O - одностадийная оплата, 'T' - двухстадийная
            'DATA': {
                "Id": userData.get('id', ''),
                "FamilyName": userData.get('familyname', ''),
                "GivenName": userData.get('givenname', ''),
                "MiddleName": userData.get('middlename', ''),
                "Email": userData.get('email', ''),
                "Phone": userData.get('tel', '')
            },

            **({'Receipt': {
                'Items': [{
                    'Name': g['title'][:128],
                    'Price': int(goods['cost'] * 100), # стоимость за единицу в копейках
                    'Quantity': goods.get('amount', 1), # количество товара
                    'Amount': int(int(goods['cost'] * 100) * goods.get('amount', 1)), # итоговая сумма в копейках
                    'Tax': CONFIG.goods_tax_delicates if goods['isdelicates'] else CONFIG.goods_tax_default,  # Обычная НДС для всех товаров и 22% для деликатесов
                    'PaymentMethod': 'full_payment',  # Полная оплата (не частичная и не кредит)
                    'PaymentObject': 'commodity' # Говорим что продаем товар, а не услугу и др
                } for g in goods],
                'Taxation': CONFIG.company_taxation_type,  # УСН доходы
                'Email': userData.get('email', ''),
                'Phone': userData.get('tel', '')
            }} if len(goods) else {}),
        }
    )

# =========== Cards / Customer Methods =============

# def addCustomer(userData) -> PaymentResponse:
#     return __sendPaymentRequest(
#         CONFIG.tbank.add_customer_url,
#         {
#             'CustomerKey': userData['id'],
#             **({'Email': userData['email']} if userData['email'] else {}),
#             **({'Phone': userData['tel']} if userData['tel'] else {}),
#         },
#     )

# def addCard(userData) -> PaymentResponse:
#     return __sendPaymentRequest(
#         CONFIG.tbank.add_card_url,
#         {
#             'CustomerKey': userData['id'],
#         },
#     )

# def getCardsList(userData) -> PaymentResponse:
#     return __sendPaymentRequest(
#         CONFIG.tbank.get_card_list_url,
#         {
#             'CustomerKey': userData,
#         },
#     )