import base64
import hashlib
from src.config import CONFIG
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend


def hash_sha256(auth_string: str) -> str:
    return hashlib.sha256(auth_string.encode('utf-8')).hexdigest()

def generateToken(params):
    tokenParams = []
    for key, value in params.items():
        # Если вдруг токен уже есть - пропускаем его
        if key == 'Token':
            continue
        # Исключаем ВСЕ вложенные объекты (DATA, Receipt и т.д.)
        if isinstance(value, (dict, list)):
            continue
        if value is not None:
            tokenParams.append({key: str(value)})
    
    # Добавляем пароль, сортируем и склеиваем в строку
    tokenParams.append({"Password": CONFIG.tbank.terminal_password})
    tokenParams.sort(key=lambda x: list(x.keys())[0].lower())
    token_string = ''.join(list(param.values())[0] for param in tokenParams)
    
    return hash_sha256(token_string)


def build_digest_string(params: dict) -> str:
    """
    Собирает строку для подписи согласно документации:
    1. Исключает DigestValue, SignatureValue, X509SerialNumber, DATA
    2. Сортирует по ключам с учётом регистра
    3. Конкатенирует значения
    """
    excluded = {'DigestValue', 'SignatureValue', 'X509SerialNumber', 'DATA'}
    token_params = []

    for key, value in params.items():
        if key in excluded:
            continue
        if value is None:
            continue
        token_params.append({key: str(value)})

    # Сортировка по ключам С УЧЁТОМ РЕГИСТРА (важно!)
    token_params.sort(key=lambda x: list(x.keys())[0])

    return ''.join(list(param.values())[0] for param in token_params)


def sign_payout_request_rsa(params: dict) -> dict:
    """
    Подписывает запрос с помощью RSA-сертификата.

    Возвращает params с добавленными DigestValue, SignatureValue, X509SerialNumber.
    """
    digest_string = build_digest_string(params)

    # 1. Считаем SHA256-хеш
    digest_bytes = hashlib.sha256(digest_string.encode('utf-8')).digest()

    # 2. DigestValue = Base64 от бинарного хеша
    digest_value = base64.b64encode(digest_bytes).decode('utf-8')

    # 3. Подписываем хеш закрытым RSA-ключом
    #    (здесь должен быть вызов вашей crypto-библиотеки)
    signature_bytes = rsa_sign(digest_bytes, CONFIG.tbank.payout_private_key_path)
    signature_value = base64.b64encode(signature_bytes).decode('utf-8')

    params['DigestValue'] = digest_value
    params['SignatureValue'] = signature_value
    params['X509SerialNumber'] = CONFIG.tbank.payout_cert_serial_number

    return params


def rsa_sign(data: bytes, private_key_path: str) -> bytes:
    """
    Подписывает данные (бинарный хеш) закрытым RSA-ключом.
    
    Args:
        data: Бинарные данные для подписи (SHA256-хеш от строки параметров)
        private_key_path: Путь к файлу с приватным ключом (PEM-формат)
    
    Returns:
        Бинарная подпись
    """
    # 1. Загружаем приватный ключ
    with open(private_key_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,  # Если ключ зашифрован паролем, укажите его здесь
            backend=default_backend()
        )
    
    # 2. Подписываем данные с использованием PKCS#1 v1.5 и SHA256
    #    Это соответствует алгоритму 'sha256RSA' из документации Т-Банка[citation:9]
    signature = private_key.sign(
        data,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    
    return signature