from dataclasses import dataclass

HTTP_INVALID_DATA = 400
HTTP_INVALID_AUTH_DATA = 401
HTTP_NO_PERMISSIONS = 403
HTTP_NOT_FOUND = 404
HTTP_DATA_CONFLICT = 409
HTTP_TEAPOT = 418
HTTP_NOT_FULL_DATA = 424
HTTP_INTERNAL_ERROR = 500
HTTP_OK = 200

@dataclass
class OrderStatuses:
    created = 'created'
    accepted = 'accepted'
    prepared = 'prepared'
    delivered = 'delivered'
    cancelled = 'cancelled'

@dataclass
class OrderPaymentStatuses:
    new = 'new'
    authorized = 'authorized'
    confirmed = 'confirmed'
    expired = 'expired'
    rejected = 'rejected'
    refunded = 'refunded'    
    cancelled = 'cancelled'    

@dataclass
class PaymentStatuses:
    """Статусы платежа Tinkoff"""
    NEW = 'NEW'  # Платеж создан
    AUTHORIZED = 'AUTHORIZED'  # Платеж авторизован
    CONFIRMED = 'CONFIRMED'  # Платеж подтвержден
    CANCELLED = 'CANCELLED'  # Платеж отменен до авторизации
    REVERSED = 'REVERSED'  # Платеж отменен
    PARTIAL_REVERSED = 'PARTIAL_REVERSED'  # Платеж отменен частично
    REFUNDED = 'REFUNDED'  # Возврат выполнен
    PARTIAL_REFUNDED = 'PARTIAL_REFUNDED'  # Частичный возврат
    REJECTED = 'REJECTED'  # Платеж отклонен
    DEADLINE_EXPIRED = 'DEADLINE_EXPIRED'  # Срок жизни платежа истек
    CHECKING_3DS = '3DS_CHECKING'  # Идет проверка 3DS
    CHECKED_3DS = '3DS_CHECKED'  # Проверка 3DS завершена
    FORM_SHOWED = 'FORM_SHOWED'  # Форма показана