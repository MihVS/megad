from enum import Enum


class EnumMegaD(Enum):
    """Базовый класс пречислений для MegaD"""

    @classmethod
    def description(cls) -> dict:
        return {}

    @classmethod
    def get_value(cls, value_plc: str):
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
    IN = 'binary_sensor'
    OUT = 'out'
    DSEN = 'digital_sensor'
    I2C = 'i2c'
    ADC = 'analog_sensor'

    @classmethod
    def description(cls) -> dict:
        return {
            '255': 'not_configured',
            '0': 'binary_sensor',
            '1': 'out',
            '2': 'digital_sensor',
            '3': 'i2c',
            '4': 'analog_sensor'
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

    NONE = None
    DOOR = 'door'
    GARAGE_DOOR = 'garage_door'
    LOCK = 'lock'
    MOISTURE = 'moisture'
    MOTION = 'motion'
    SMOKE = 'smoke'
    WINDOW = 'window'


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

    SWITCH = 'switch'
    LIGHT = 'light'
    FAN = 'fan'


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
            '0': 'dth11',
            '1': 'dth22',
            '2': 'one_wire',
            '3': 'one_wire_bus',
            '4': 'i_button',
            '5': 'wiegand_26'
        }
