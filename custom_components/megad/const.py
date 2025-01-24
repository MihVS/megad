from collections import namedtuple

from homeassistant.const import (
    UnitOfTemperature, PERCENTAGE, CONCENTRATION_PARTS_PER_MILLION
)
from homeassistant.components.sensor.const import SensorDeviceClass

DOMAIN = 'megad'
MANUFACTURER = 'ab-log'

# Таймауты
TIME_UPDATE = 60
TIME_OUT_UPDATE_DATA = 5

COUNTER_CONNECT = 0

PATH_CONFIG_MEGAD = './config/custom_components/megad/config_megad/'

# Значения по умолчанию
DEFAULT_IP = '192.168.0.14'
DEFAULT_PASSWORD = 'sec'

# Поля в интерфейсе MegaD
TITLE_MEGAD = 'emt'
NAME_SCRIPT_MEGAD = 'sct'

# Обозначения категорий статусов сенсоров в MegaD
TEMPERATURE = 'temp'
HUMIDITY = 'hum'
CO2 = 'CO2'

PLC_BUSY = 'busy'

# Номера страниц конфигураций для запроса
START_CONFIG = 0
MAIN_CONFIG = 1
ID_CONFIG = 2
VIRTUAL_PORTS_CONFIG = 5

# Параметры запроса MegaD
VALUE = 'v'
COUNT = 'cnt'
MODE = 'm'
CLICK = 'click'

StateButton = namedtuple('StateButton', ['SINGLE', 'DOUBLE', 'LONG', 'OFF'])
STATE_BUTTON = StateButton(SINGLE="single", DOUBLE="double", LONG="long", OFF="off")

PortCommand = namedtuple('PortCommand', ['ON', 'OFF', 'TOGGLE'])
PORT_COMMAND = PortCommand(ON='1', OFF='0', TOGGLE='2')

SENSOR_UNIT = {
    TEMPERATURE: UnitOfTemperature.CELSIUS,
    HUMIDITY: PERCENTAGE,
    CO2: CONCENTRATION_PARTS_PER_MILLION
}

SENSOR_CLASS = {
    TEMPERATURE: SensorDeviceClass.TEMPERATURE,
    HUMIDITY: SensorDeviceClass.HUMIDITY,
    CO2: SensorDeviceClass.CO2
}

STATE_RELAY = ['on', 'off', '1', '0']
RELAY_ON = ['1', 'on']
RELAY_OFF = ['0', 'off']

PLATFORMS = [
    'binary_sensor',
    'sensor',
    'switch',
    'light',
    'fan',
]
