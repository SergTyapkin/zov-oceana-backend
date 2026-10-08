from dataclasses import dataclass
import threading


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

@dataclass
class PayoutStatuses:
    """Статусы исходящего платежа Tinkoff через СБП"""
    CHECKED = 'CHECKED'  # Инициализирована
    COMPLETING = 'COMPLETING'
    COMPLETED = 'COMPLETED'
    REJECTED = 'REJECTED'
    UNKNOWN = 'UNKNOWN'


class PaymentResponse:
    # ===== Общие поля =====
    success: bool
    errorCode: str
    message: str | None
    details: str | None

    # ===== Платёжные поля =====
    id: str | None                 # Init, Cancel, Confirm, GetState
    orderId: str | None            # Init, Cancel, Confirm, GetState
    # Special responses types fields
    status: PaymentStatuses | None # Init, Cancel, Confirm, GetState
    paymentUrl: str | None         # Init
    amount: int | None             # Init, Cancel, Confirm, GetState (если присылалась в запросе)
    # RebillId: str | None         # Confirm, Cancel
    # CardId: str | None           # Confirm, Cancel
    qrData: str | None             # GetQR
    route: str | None              # GetState
    source: str | None             # GetState

    # ===== Поля покупателя / карт =====
    customerKey: str | None             # AddCustomer
    requestKey: str | None              # AddCard
    cardId: str | None                  # AddCard
    rebillId: str | None                # AddCard
    pan: str | None                     # AddCard (маскированный номер)
    cards: list[dict[str, any]] | None  # GetCardList
    # { CardId (String) — идентификатор карты в системе Банка
    #   Pan (String) — маскированный номер карты, например "543211******4773"
    #   Status (String) — статус карты: "A" (активная), "I" (неактивная), "D" (удалена)
    #   RebillId (Number) — идентификатор для рекуррентных платежей
    #   ExpDate (String) — срок действия карты в формате MMYY
    # } CardType (?Number) — тип карты

    # ===== Поля payouts =====
    members: list[dict[str, any]] | None  # GetSPBMembers
    # { MemberId (String) — идентификатор банка
    #   MemberName (String) — международное название банка
    # } MemberNameRus (String) — русское название банка
    
    def __init__(self, response):
        data = response.json()
        print("> PAYMENT RESPONSE FROM TINKOFF:", data)

        # ===== Базовые поля =====
        self.success = data.get("Success", False)
        self.errorCode = data.get("ErrorCode", "")
        self.message = data.get("Message")
        self.details = data.get("Details")

        # ===== Платёжные поля =====
        self.id = data.get("PaymentId")
        raw_order_id = data.get("OrderId")
        self.orderId = raw_order_id.split("_")[0] if raw_order_id else None

        self.status = data.get("Status")
        self.paymentUrl = data.get("PaymentURL")
        self.amount = data.get("Amount")
        self.qrData = data.get("Data")
        
        # ===== Route / Source (GetState) =====
        self.route = None
        self.source = None
        params: list[dict[str, str]] = data.get("Params", [])
        for param in params:
            if param.get("Key") == "Route":
                self.route = param.get("Value")
            elif param.get("Key") == "Source":
                self.source = param.get("Value")

        # ===== Покупатель / карты =====
        self.customerKey = data.get("CustomerKey")
        self.requestKey = data.get("RequestKey")
        self.cardId = data.get("CardId")
        self.rebillId = data.get("RebillId")
        self.pan = data.get("Pan")

        # ===== GetCardList может вернуть как список, так и объект =====
        if isinstance(data, list):
            self.cards = data
        elif isinstance(data.get("Cards"), list):
            self.cards = data["Cards"]
        else:
            self.cards = None

        # ===== GetSBPMembers может вернуть как список, так и объект =====
        if isinstance(data, list):
            self.members = data
        elif isinstance(data.get("Members"), list):
            self.members = data["Members"]
        else:
            self.members = None


class OrderPollingThreadData:
    thread: threading.Thread
    awaitingForStatuses: list[PaymentStatuses] | None
    stop_flag: threading.Event
    def __init__(self, thread, awaitingForStatuses, stop_flag):
        self.thread = thread
        self.awaitingForStatuses = awaitingForStatuses
        self.stop_flag = stop_flag
