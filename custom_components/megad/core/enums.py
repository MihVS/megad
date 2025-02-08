from enum import Enum


class EnumMegaD(Enum):
    """Базовый класс перечислений для MegaD"""

    @classmethod
    def description(cls) -> dict:
        return {}

    @classmethod
    def get_value(cls, value_plc):
        value_plc = str(value_plc).rstrip()
        return cls.description().get(value_plc)

    @property
    def value_plc(self):
        """Значение контроллера."""

        return {v: k for k, v in self.description().items()}.get(self.value)


class ServerTypeMegaD(EnumMegaD):
    """Протокол общения с сервером"""

    HTTP = 'http'
    MQTT = 'mqtt'

    @classmethod
    def description(cls) -> dict:
        return {
            '0': 'http',
            '1': 'mqtt'
        }


class ConfigUARTMegaD(EnumMegaD):
    """Настройка поля UART"""

    DISABLED = 'disabled'
    GSM = 'gsm'
    RS485 = 'rs485'

    @classmethod
    def description(cls) -> dict:
        return {
            '0': 'disabled',
            '1': 'gsm',
            '2': 'rs485'
        }


class TypeNetActionMegaD(EnumMegaD):
    """Типы действия поля NetAction"""

    D = 'default'
    SF = 'server_failure'
    A = 'actions'

    @classmethod
    def description(cls) -> dict:
        return {
            '0': 'default',
            '1': 'server_failure',
            '2': 'actions'
        }


class TypePortMegaD(EnumMegaD):
    """Типы портов контроллера"""

    NC = 'not_configured'
    IN = 'in'
    OUT = 'out'
    DSEN = 'digital_sensor'
    I2C = 'i2c'
    ADC = 'analog_sensor'

    @classmethod
    def description(cls) -> dict:
        return {
            '255': 'not_configured',
            '0': 'in',
            '1': 'out',
            '3': 'digital_sensor',
            '4': 'i2c',
            '2': 'analog_sensor'
        }


class ModeInMegaD(EnumMegaD):
    """Типы настройки Mode входов"""

    P = 'press'
    P_R = 'press_release'
    R = 'release'
    C = 'click'

    @classmethod
    def description(cls) -> dict:
        return {
            '0': 'press',
            '1': 'press_release',
            '2': 'release',
            '3': 'click',
        }


class DeviceClassBinary(Enum):
    """Бинарные классы Home Assistant"""

    NONE = ''
    DOOR = 'd'
    GARAGE_DOOR = 'gd'
    LOCK = 'l'
    MOISTURE = 'ms'
    MOTION = 'm'
    SMOKE = 's'
    WINDOW = 'w'


class ModeOutMegaD(EnumMegaD):
    """Типы настройки Mode выходов"""

    SW = 'relay'
    PWM = 'pwm'
    DS2413 = 'one_wire_modul'
    SW_LINK = 'relay_link'
    WS281X = 'rgb_tape'

    @classmethod
    def description(cls) -> dict:
        return {
            '0': 'relay',
            '1': 'pwm',
            '2': 'one_wire_modul',
            '3': 'relay_link',
            '4': 'rgb_tape',
        }


class DeviceClassControl(Enum):
    """Класс управления в Home Assistant"""

    SWITCH = 's'
    LIGHT = 'l'
    FAN = 'f'


class DeviceClassClimate(Enum):
    """Класс температурных режимов термостата в Home Assistant"""

    HOME = 'h'
    BOILER = 'b'
    CELLAR = 'c'
    FLOOR = 'f'


class TypeDSensorMegaD(EnumMegaD):
    """Типы настройки Mode выходов TypeDSensorMegaD"""

    DHT11 = 'dth11'
    DHT22 = 'dth22'
    ONEW = 'one_wire'
    ONEWBUS = 'one_wire_bus'
    iB = 'i_button'
    W26 = 'wiegand_26'

    @classmethod
    def description(cls) -> dict:
        return {
            '1': 'dth11',
            '2': 'dth22',
            '3': 'one_wire',
            '5': 'one_wire_bus',
            '4': 'i_button',
            '6': 'wiegand_26'
        }


class ModeSensorMegaD(EnumMegaD):
    """Типы настройки Mode сенсоров"""

    NORM = 'norm'
    MORE = 'more'
    LESS = 'less'
    LESS_AND_MORE = 'less_and_more'

    @classmethod
    def description(cls) -> dict:
        return {
            '0': 'norm',
            '1': 'more',
            '2': 'less',
            '3': 'less_and_more'
        }


class ModeWiegandMegaD(EnumMegaD):
    """Типы настройки mode Wiegand 26"""

    NC = 'not_configured'
    D0 = 'd0'
    D1 = 'd1'

    @classmethod
    def description(cls) -> dict:
        return {
            '0': 'not_configured',
            '1': 'd0',
            '2': 'd1'
        }


class ModeI2CMegaD(EnumMegaD):
    """Типы настройки mode I2C"""

    NC = 'not_configured'
    SDA = 'sda'
    SCL = 'scl'

    @classmethod
    def description(cls) -> dict:
        return {
            '0': 'not_configured',
            '1': 'sda',
            '2': 'scl'
        }


class CategoryI2CMegaD(EnumMegaD):
    """Категории I2C"""

    ANY = 'any'
    TEMP_HUM = 'temp_hum'
    LIGHT = 'light'
    EXPANDER = 'expander'
    MISC = 'misc'
    AIR_QUALITY = 'air_quality'

    @classmethod
    def description(cls) -> dict:
        return {
            '0': 'any',
            '1': 'temp_hum',
            '2': 'light',
            '3': 'expander',
            '4': 'misc',
            '5': 'air_quality'
        }


class DeviceI2CMegaD(EnumMegaD):
    """Девайсы I2C"""

    NC = 'not_configured'
    HTU21D = 'htu21d'
    SHT31 = 'sht31'
    HTU31D = 'htu31d'
    BMP180 = 'bmp180'
    BMx280 = 'bmx280'
    BME680 = 'bme680'
    DPS368 = 'dps368'
    MLX90614 = 'mlx90614'
    MCP9600 = 'mcp9600'
    TMP117 = 'tmp117'
    CGanem = 'cganem'
    MAX44009 = 'max44009'
    OPT3001 = 'opt3001'
    BH1750 = 'bh1750'
    TSL2591 = 'tsl2591'
    MCP230XX = 'mcp230xx'
    PCA9685 = 'pca9685'
    T67xx = 't67xx'
    SCD4x = 'scd4x'
    HM3301 = 'hm3301'
    SPS30 = 'sps30'
    SSD1306 = 'ssd1306'
    LCD1602 = 'lcd1602'
    ADS1115 = 'ads1115'
    INA226 = 'ina226'
    Encoder = 'encoder'
    PTsensor = 'ptsensor'
    RadSens = 'radsens'

    @classmethod
    def description(cls) -> dict:
        return {
            '0': 'not_configured',
            '1': 'htu21d',
            '51': 'sht31',
            '56': 'htu31d',
            '5': 'bmp180',
            '6': 'bmx280',
            '53': 'bme680',
            '55': 'dps368',
            '50': 'mlx90614',
            '52': 'mcp9600',
            '54': 'tmp117',
            '57': 'cganem',
            '7': 'max44009',
            '70': 'opt3001',
            '2': 'bh1750',
            '3': 'tsl2591',
            '20': 'mcp230xx',
            '21': 'pca9685',
            '40': 't67xx',
            '44': 'scd4x',
            '41': 'hm3301',
            '42': 'sps30',
            '4': 'ssd1306',
            '80': 'lcd1602',
            '60': 'ADS1115',
            '61': 'ina226',
            '30': 'encoder',
            '90': 'ptsensor',
            '100': 'radsens',
        }


class ModePIDMegaD(EnumMegaD):
    """Типы настройки Mode ПИД"""

    HEAT = 'heat'
    COOL = 'cool'
    BALANCE = 'balance'

    @classmethod
    def description(cls) -> dict:
        return {
            '0': 'heat',
            '1': 'cool',
            '2': 'balance',
        }
