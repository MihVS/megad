from collections import namedtuple

from .core.enums import DeviceClassClimate
from homeassistant.const import (
    UnitOfTemperature, PERCENTAGE, CONCENTRATION_PARTS_PER_MILLION, UnitOfTime
)
from homeassistant.components.sensor.const import SensorDeviceClass

DOMAIN = 'megad'
MANUFACTURER = 'ab-log'
ENTRIES = 'entries'
CURRENT_ENTITY_IDS = 'current_entity_ids'

# Таймауты
TIME_UPDATE = 60
TIME_OUT_UPDATE_DATA = 5
TIME_SLEEP_REQUEST = 0.2

COUNT_UPDATE = 20
COUNTER_CONNECT = 0

PATH_CONFIG_MEGAD = 'custom_components/config_megad/'

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
UPTIME = 'uptime'

# Перевод сенсоров
TYPE_SENSOR_RUS = {
    TEMPERATURE: 'температура',
    HUMIDITY: 'влажность',
    CO2: 'CO2'
}

STATUS_THERMO = 'status_thermo'

PLC_BUSY = 'busy'
PORT_OFF = 'off'
NOT_AVAILABLE = 'NA'

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
PORT = 'pt'
COMMAND = 'cmd'
ALL_STATES = 'all'
LIST_STATES = 'list'
SCL_PORT = 'scl'
I2C_DEVICE = 'i2c_dev'
DIRECTION = 'dir'
SET_TEMPERATURE = 'misc'
CONFIG = 'cf'
PID = 'pid'
PID_E = 'pide'
PID_SET_POINT = 'pidsp'
PID_INPUT = 'pidi'

# Значения запроса
ON = 1
OFF = 0
PID_OFF = 255

# Параметры ответа MegaD
MEGAD_ID = 'mdid'
MEGAD_STATE = 'st'
PORT_ID = 'pt'

StateButton = namedtuple('StateButton', ['SINGLE', 'DOUBLE', 'LONG', 'OFF'])
STATE_BUTTON = StateButton(SINGLE="single", DOUBLE="double", LONG="long", OFF="off")

PortCommand = namedtuple('PortCommand', ['ON', 'OFF', 'TOGGLE'])
PORT_COMMAND = PortCommand(ON='1', OFF='0', TOGGLE='2')

SENSOR_UNIT = {
    TEMPERATURE: UnitOfTemperature.CELSIUS,
    HUMIDITY: PERCENTAGE,
    CO2: CONCENTRATION_PARTS_PER_MILLION,
    UPTIME: UnitOfTime.MINUTES
}

SENSOR_CLASS = {
    TEMPERATURE: SensorDeviceClass.TEMPERATURE,
    HUMIDITY: SensorDeviceClass.HUMIDITY,
    CO2: SensorDeviceClass.CO2,
    UPTIME: SensorDeviceClass.DURATION
}

TEMPERATURE_CONDITION = {
    DeviceClassClimate.HOME: (5, 30),
    DeviceClassClimate.BOILER: (30, 80),
    DeviceClassClimate.CELLAR: (0, 20),
    DeviceClassClimate.FLOOR: (15, 45)
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
    'climate'
]
