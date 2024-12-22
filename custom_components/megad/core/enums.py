from enum import Enum


class ServerTypeMegaD(str, Enum):
    """Протокол общения с сервером"""

    HTTP = 'http'
    MQTT = 'mqtt'
    NONE = ''


class ConfigUARTMegaD(str, Enum):
    """Настройка поля UART"""

    DISABLED = 'disabled'
    GSM = 'gsm'
    RS485 = 'rs485'
    NONE = ''


class TypeNetActionMegaD(str, Enum):
    """Типы действия поля NetAction"""

    D = 'default'
    SF = 'server_failure'
    A = 'actions'


class TypePortMegaD(str, Enum):
    """Типы портов контроллера"""

    NC = 'not_configured'
    IN = 'binary_sensor'
    OUT = 'out'
    DSEN = 'digital_sensor'
    I2C = 'i2c'
    ADC = 'analog_sensor'


class ModeInMegaD(str, Enum):
    """Типы настройки Mode входов"""

    P = 'press'
    P_R = 'press_release'
    R = 'release'
    C = 'click'


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


class ModeOutMegaD(str, Enum):
    """Типы настройки Mode выходов"""

    SW = 'relay'
    PWM = 'pwm'
    DS2413 = 'one_wire_modul'
    SW_LINK = 'relay_link'
    WS281X = 'rgb_tape'


class DeviceClassControl(Enum):
    """Класс управления в Home Assistant"""

    SWITCH = 'switch'
    LIGHT = 'light'
    FAN = 'fan'
