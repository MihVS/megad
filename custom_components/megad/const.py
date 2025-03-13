from collections import namedtuple
from dataclasses import dataclass

from .core.enums import DeviceClassClimate
from homeassistant.const import (
    UnitOfTemperature, PERCENTAGE, CONCENTRATION_PARTS_PER_MILLION, UnitOfTime,
    UnitOfPressure
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
RELEASE_URL = 'https://ab-log.ru/smart-house/ethernet/megad-2561-firmware'

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
PRESSURE = 'press'

# Перевод сенсоров
TYPE_SENSOR_RUS = {
    TEMPERATURE: 'температура',
    HUMIDITY: 'влажность',
    CO2: 'CO2',
    PRESSURE: 'давление'
}

STATUS_THERMO = 'status_thermo'

PLC_BUSY = 'busy'
PORT_OFF = 'off'
NOT_AVAILABLE = 'NA'
MCP_MODUL = 'MCP'
PCA_MODUL = 'PCA'

# Номера страниц конфигураций для запроса
START_CONFIG = 0
MAIN_CONFIG = 1
ID_CONFIG = 2
VIRTUAL_PORTS_CONFIG = 5
CRON = 7

# Параметры ПИД
P_FACTOR = 'p_factor'
I_FACTOR = 'i_factor'
D_FACTOR = 'd_factor'
VALUE_PID = 'value'
INPUT_PID = 'input'
TARGET_TEMP = 'set_point'
STEP_FACTOR = 0.01

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
PID_P_FACTOR = 'pidpf'
PID_I_FACTOR = 'pidif'
PID_D_FACTOR = 'piddf'
SET_TIME = 'stime'

# Значения запроса
ON = 1
OFF = 0
PID_OFF = 255
GET_STATUS = 'get'

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
    PRESSURE: UnitOfPressure.MMHG,
    UPTIME: UnitOfTime.MINUTES
}

SENSOR_CLASS = {
    TEMPERATURE: SensorDeviceClass.TEMPERATURE,
    HUMIDITY: SensorDeviceClass.HUMIDITY,
    CO2: SensorDeviceClass.CO2,
    PRESSURE: SensorDeviceClass.PRESSURE,
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
    'climate',
    'number',
    'update'
]


@dataclass(frozen=True)
class PIDLimit:
    """Лимиты для коэффициентов ПИД-регулятора."""
    min_value: float
    max_value: float


PID_LIMIT_P = PIDLimit(min_value=0.0, max_value=100.0)
PID_LIMIT_I = PIDLimit(min_value=0.0, max_value=10.0)
PID_LIMIT_D = PIDLimit(min_value=0.0, max_value=10.0)
