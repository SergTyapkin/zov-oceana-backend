import os
from dataclasses import dataclass, field
from typing import Optional, Any
from pathlib import Path
from dotenv import load_dotenv


@dataclass
class DatabaseConfig:
    user: str
    host: str
    port: int
    name: str
    password: str


@dataclass
class TbankConfig:
    terminal_key: str
    terminal_password: str
    use_two_stage_payments: bool
    max_order_pay_time_sec: int = 900  # 15 минут
    init_url: str = 'https://securepay.tinkoff.ru/v2/Init'
    confirm_url: str = 'https://securepay.tinkoff.ru/v2/Confirm'
    cancel_url: str = 'https://securepay.tinkoff.ru/v2/Cancel'
    refund_url: str = 'https://securepay.tinkoff.ru/v2/Refund'
    get_qr_url: str = 'https://securepay.tinkoff.ru/v2/GetQr'
    get_state_url: str = 'https://securepay.tinkoff.ru/v2/GetState'


@dataclass
class EmailConfig:
    smtp_host: str
    smtp_port: int
    smtp_use_tls: bool
    address: str
    sender_name: str
    password: str


@dataclass
class TelegramConfig:
    bot_token: str
    bot_enabled: bool = False


@dataclass
class AppConfig:
    # Основные
    debug: bool = True
    host: str = '0.0.0.0'
    port: int = 9000
    project_name: str = "ZovOceana"
    deploy_full_url: str = 'https://zovoceana.ru'
    deploy_short_url: str = 'zovoceana.ru'

    # База данных
    db: DatabaseConfig = field(default_factory=DatabaseConfig)

    # T-Банк
    tbank: TbankConfig = field(default_factory=TbankConfig)

    # Почта
    email: EmailConfig = field(default_factory=EmailConfig)

    # Telegram
    telegram: TelegramConfig = field(default_factory=TelegramConfig)

    # Картинки
    save_images_to_db: bool = False
    save_images_folder: str = './images'
    max_image_size_px: int = 2048
    image_uid_generate_len: int = 30

    # Логи
    max_log_data_length: int = 512

    # Генерация кодов
    order_secret_code_generate_len: int = 6
    max_order_number: int = 999999
    order_number_seed: int = 5901273812

    # Авторизация
    allow_tg_auth_period_min: int = 30

    # Маркетинг
    order_cost_percent_to_referrer_bonuses: float = 0.10
    order_cost_percent_to_referrer_ahead_1_bonuses: float = 0.08

    # CORS
    cors_origins: list = field(default_factory=lambda: [
        "http://localhost",
        "https://localhost",
        "http://127.0.0.1",
        "https://127.0.0.1"
    ])

    # Фискализация
    company_taxation_type: str = 'usn_income'
    goods_tax_default: str = 'vat10'
    goods_tax_delicates: str = 'vat22'

    # GeoLite2
    geolite_db_path: str = 'configs/GeoLite2-City.mmdb'


class Config:
    """Синглтон для доступа к конфигурации"""
    _instance: Optional['Config'] = None
    _config: Optional[AppConfig] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            self._load_config()

    def _load_config(self):
        """Загружает конфигурацию из .env файла и системных переменных"""
        # Загружаем .env из папки запуска
        env_path = Path.cwd() / '.env'
        if env_path.exists():
            load_dotenv(env_path)
        else:
            print(f"⚠️ .env файл не найден в {env_path}")

        # Функция для получения переменной с приоритетом: .env > системный env
        def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
            # Сначала проверяем в os.environ (туда загрузился .env)
            value = os.environ.get(key)
            if value is not None:
                return value
            # Если нет в .env, проверяем системный env (но он уже там же)
            return default

        # Функция для получения обязательной переменной
        def get_required_env(key: str) -> str:
            value = get_env(key)
            if value is None:
                raise ValueError(f"❌ Обязательная переменная {key} не найдена в .env или системе")
            return value

        # Функция для парсинга CORS
        def parse_cors(value: str) -> list:
            return [item.strip() for item in value.split(',') if item.strip()]

        try:
            # Собираем конфиг
            self._config = AppConfig(
                debug=get_env('DEBUG', 'False').lower() == 'true',
                host=get_required_env('HOST'),
                port=int(get_required_env('PORT')),
                project_name=get_required_env('PROJECT_NAME'),
                deploy_full_url=get_required_env('DEPLOY_FULL_URL'),
                deploy_short_url=get_required_env('DEPLOY_SHORT_URL'),

                db=DatabaseConfig(
                    user=get_required_env('POSTGRES_USER'),
                    host=get_required_env('POSTGRES_HOST'),
                    port=int(get_required_env('POSTGRES_PORT')),
                    name=get_required_env('POSTGRES_DB'),
                    password=get_required_env('POSTGRES_PASSWORD')
                ),

                tbank=TbankConfig(
                    terminal_key=get_required_env('TBANK_TERMINAL_KEY'),
                    terminal_password=get_required_env('TBANK_TERMINAL_PASSWORD'),
                    max_order_pay_time_sec=int(get_env('MAX_ORDER_PAY_TIME_SEC', '900')),
                    use_two_stage_payments=get_env('USE_TWO_STAGE_PAYMENTS', 'True').lower() == 'true',
                    init_url=get_env('TBANK_INIT_URL', 'https://securepay.tinkoff.ru/v2/Init'),
                    confirm_url=get_env('TBANK_CONFIRM_URL', 'https://securepay.tinkoff.ru/v2/Confirm'),
                    cancel_url=get_env('TBANK_CANCEL_URL', 'https://securepay.tinkoff.ru/v2/Cancel'),
                    refund_url=get_env('TBANK_REFUND_URL', 'https://securepay.tinkoff.ru/v2/Refund'),
                    get_qr_url=get_env('TBANK_GET_QR_URL', 'https://securepay.tinkoff.ru/v2/GetQr'),
                    get_state_url=get_env('TBANK_GET_STATE_URL', 'https://securepay.tinkoff.ru/v2/GetState'),
                ),

                email=EmailConfig(
                    smtp_host=get_required_env('SMTP_MAIL_SERVER_HOST'),
                    smtp_port=int(get_required_env('SMTP_MAIL_SERVER_PORT')),
                    smtp_use_tls=get_env('SMTP_MAIL_SERVER_USE_TLS', 'True').lower() == 'true',
                    address=get_required_env('MAIL_ADDRESS'),
                    sender_name=get_required_env('MAIL_SENDER_NAME'),
                    password=get_required_env('MAIL_PASSWORD')
                ),

                telegram=TelegramConfig(
                    bot_token=get_env('TG_BOT_TOKEN', ''),
                    bot_enabled=get_env('TG_BOT_ENABLED', 'False').lower() == 'true'
                ),

                save_images_to_db=get_env('SAVE_IMAGES_TO_DB', 'False').lower() == 'true',
                save_images_folder=get_env('SAVE_IMAGES_FOLDER', './images'),
                max_image_size_px=int(get_env('MAX_IMAGE_SIZE_PX', '2048')),
                image_uid_generate_len=int(get_env('IMAGE_UID_GENERATE_LEN', '30')),

                max_log_data_length=int(get_env('MAX_LOG_DATA_LENGTH', '512')),

                order_secret_code_generate_len=int(get_env('ORDER_SECRET_CODE_GENERATE_LEN', '6')),
                max_order_number=int(get_env('MAX_ORDER_NUMBER', '999999')),
                order_number_seed=int(get_env('ORDER_NUMBER_SEED', '5901273812')),

                allow_tg_auth_period_min=float(get_env('ALLOW_TG_AUTH_PERIOD_MIN', '30')),

                order_cost_percent_to_referrer_bonuses=float(get_env('ORDER_COST_PERCENT_TO_REFERRER_BONUSES', '0.10')),
                order_cost_percent_to_referrer_ahead_1_bonuses=float(get_env('ORDER_COST_PERCENT_TO_REFERRER_AHEAD_1_BONUSES', '0.08')),

                cors_origins=parse_cors(get_env('CORS_ORIGINS', 'http://localhost,https://localhost,http://127.0.0.1,https://127.0.0.1')),

                company_taxation_type=get_env('COMPANY_TAXATION_TYPE', 'usn_income'),
                goods_tax_default=get_env('GOODS_TAX_DEFAULT', 'vat10'),
                goods_tax_delicates=get_env('GOODS_TAX_DELICATES', 'vat22'),

                geolite_db_path=get_env('GEOLITE_DB_PATH', 'configs/GeoLite2-City.mmdb')
            )

            # Создаем папку для картинок, если нужно
            if not self._config.save_images_to_db:
                folder = Path(self._config.save_images_folder)
                if not folder.exists():
                    print(f"📁 Создаю папку для картинок: {folder}")
                    folder.mkdir(parents=True, exist_ok=True)

            print(f"✅ Конфигурация загружена успешно")
            print(f"   📦 Проект: {self._config.project_name}")
            print(f"   🗄️  БД: {self._config.db.user}@{self._config.db.host}:{self._config.db.port}/{self._config.db.name}")
            print(f"   🔑 T-Банк: {self._config.tbank.terminal_key}")
            print(f"   📧 Почта: {self._config.email.address}")

        except ValueError as e:
            print(f"❌ Ошибка загрузки конфигурации: {e}")
            raise
        except Exception as e:
            print(f"❌ Непредвиденная ошибка при загрузке конфигурации: {e}")
            raise

    @property
    def config(self) -> AppConfig:
        if self._config is None:
            self._load_config()
        return self._config

    def __getattr__(self, name: str) -> Any:
        """Позволяет обращаться к полям конфига напрямую: CONFIG.db.password"""
        if self._config is None:
            self._load_config()
        return getattr(self._config, name)

    def __getitem__(self, key: str) -> Any:
        """Позволяет обращаться через квадратные скобки: CONFIG['db']['password']"""
        if self._config is None:
            self._load_config()
        return getattr(self._config, key)


# Создаем глобальный экземпляр конфига
CONFIG = Config()

# Для удобного импорта из других модулей
# from src.config import CONFIG
# CONFIG.db.password
# CONFIG.tbank.terminal_key