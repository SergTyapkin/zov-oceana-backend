import hashlib
import json
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TERMINAL_KEY = "1781187421158DEMO"
PASSWORD = "Qz$$Gd2Rx4*&8t9U"

def generate_token(params, password):
    token_params = []
    for key, value in params.items():
        # Если вдруг токен уже есть - пропускаем его
        if key == 'Token':
            continue
        # Исключаем ВСЕ вложенные объекты (DATA, Receipt и т.д.)
        if isinstance(value, (dict, list)):
            continue
        if value is not None:
            token_params.append({key: str(value)})
    
    # Добавляем пароль, сортируем и склеиваем в строку
    token_params.append({"Password": password})
    token_params.sort(key=lambda x: list(x.keys())[0].lower())
    token_string = ''.join(list(param.values())[0] for param in token_params)

    return hashlib.sha256(token_string.encode('utf-8')).hexdigest()

# Формируем запрос
params = {
    'TerminalKey': TERMINAL_KEY,
    'Amount': 99990,
    'OrderId': '_ORDER-ID_',
    'Description': '_DESCRIPTION_',
    'CustomerKey': '_CUSTOMER_KEY_',
    'Language': 'ru',
    'PayType': 'O',
}

params['DATA'] = {
    "Phone": "+79031234567",
    "Email": "test@test.com"
}
params['Receipt'] = {
    "Taxation": "usn_income",
    "Email": "test@test.com",
    "Phone": "+79031234567",
    "Items": [
        {
            "Name": "Какой-то продукт",
            "Price": 999,
            "Quantity": 10,
            "Amount": 99990,
            "Tax": "none",
            "PaymentMethod": "full_payment",
            "PaymentObject": "commodity"
        }
    ]
}


# Генерируем токен
params['Token'] = generate_token(params, PASSWORD)

print("Request params:")
print(json.dumps(params, indent=2, ensure_ascii=False))

try:
    response = requests.post(
        'https://securepay.tinkoff.ru/v2/Init',  # или тестовый URL
        json=params,
        headers={'Content-Type': 'application/json'},
        timeout=30,
        verify=False,
    )
    
    print(f"\nStatus: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except json.JSONDecodeError:
        print(f"Raw response: {response.text}")
except Exception as e:
    print(f"Error: {e}")