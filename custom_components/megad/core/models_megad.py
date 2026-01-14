from ipaddress import IPv4Address
from urllib.parse import unquote

from pydantic import BaseModel, Field, field_validator, model_validator

from .enums import (ServerTypeMegaD, ConfigUARTMegaD, TypeNetActionMegaD,
                    TypePortMegaD, ModeInMegaD, DeviceClassBinary,
                    ModeOutMegaD, DeviceClassControl, TypeDSensorMegaD,
                    ModeSensorMegaD, ModeWiegandMegaD, ModeI2CMegaD,
                    CategoryI2CMegaD, DeviceI2CMegaD, DeviceClassClimate,
                    ModePIDMegaD)
from ..const import NOT_AVAILABLE


class SystemConfigMegaD(BaseModel):
    """Главный конфиг контроллера"""

    ip_megad: IPv4Address = Field(alias='eip')
    megad_id: str = Field(alias='mdid', default='', max_length=5)
    network_mask: IPv4Address = Field(alias='emsk', default=None)
    password: str = Field(alias='pwd', max_length=3)
    gateway: IPv4Address = Field(alias='gw')
    ip_server: str = Field(alias='sip')
    server_type: ServerTypeMegaD = Field(alias='srvt', default=0)
    slug: str = Field(alias='sct')
    uart: ConfigUARTMegaD = Field(alias='gsm')

    @field_validator('ip_server', mode='before')
    def decode_ip_and_port(cls, value):
        decoded_value = unquote(value)
        ip, port = decoded_value.split(':')
        IPv4Address(ip)
        return decoded_value

    @field_validator('server_type', mode='before')
    def convert_server_type(cls, value):
        return ServerTypeMegaD.get_value(value)

    @field_validator('uart', mode='before')
    def convert_uart_type(cls, value):
        new_value = ConfigUARTMegaD.get_value(value)
        return new_value


class PIDConfig(BaseModel):
    """Класс для ПИД терморегуляторов."""

    id: int = Field(alias='pid')
    sensor_id: int | None = Field(default=None)
    title: str = Field(alias='pidt', default='')
    input: int = Field(alias='pidi', ge=0, le=255, default=255)
    output: int = Field(alias='pido', ge=0, le=255, default=255)
    set_point: float = Field(alias='pidsp', default=0)
    p_factor: float = Field(alias='pidpf', default=0)
    i_factor: float = Field(alias='pidif', default=0)
    d_factor: float = Field(alias='piddf', default=0)
    mode: ModePIDMegaD = Field(alias='pidm')
    cycle_time: int = Field(alias='pidc', ge=0, le=255, default=0)
    value: int | None = None
    name: str = Field(default='')
    device_class: DeviceClassClimate = DeviceClassClimate.HOME

    @field_validator('value', mode='before')
    def validate_value(cls, value):
        if value == NOT_AVAILABLE:
            return None
        return int(value)

    @field_validator('input', mode='before')
    def validate_input(cls, value):
        if value == '':
            return 255
        return int(value)

    @field_validator('output', mode='before')
    def validate_output(cls, value):
        if value == '':
            return 255
        return int(value)

    @field_validator('set_point', mode='before')
    def validate_set_point(cls, value):
        if value == '':
            return 0
        return float(value)

    @field_validator('p_factor', mode='before')
    def validate_p_factor(cls, value):
        if value == '':
            return 0
        return float(value)

    @field_validator('i_factor', mode='before')
    def validate_i_factor(cls, value):
        if value == '':
            return 0
        return float(value)

    @field_validator('d_factor', mode='before')
    def validate_d_factor(cls, value):
        if value == '':
            return 0
        return float(value)

    @field_validator('cycle_time', mode='before')
    def validate_cycle_time(cls, value):
        if value == '':
            return 0
        return int(value)

    @model_validator(mode='before')
    def add_field(cls, data):
        title = data.get('pidt', '')
        name = title.split('/')[0]
        if name:
            data['name'] = name
        else:
            data['name'] = f'pid{data["pid"]}'
        if title.count('/') > 0:
            device_class = title.split('/')[1]
            match device_class:
                case DeviceClassClimate.HOME.value:
                    data.update({'device_class': DeviceClassClimate.HOME})
                case DeviceClassClimate.BOILER.value:
                    data.update({'device_class': DeviceClassClimate.BOILER})
                case DeviceClassClimate.CELLAR.value:
                    data.update({'device_class': DeviceClassClimate.CELLAR})
                case DeviceClassClimate.FLOOR.value:
                    data.update({'device_class': DeviceClassClimate.FLOOR})
        if title.count('/') > 1:
            sensor_id = title.split('/')[2]
            if sensor_id.isdigit():
                data.update({'sensor_id': sensor_id})
        return data

    @field_validator('mode', mode='before')
    def convert_type_port(cls, value):
        return ModePIDMegaD.get_value(value)


class PortConfig(BaseModel):
    """Базовый класс для всех портов"""

    id: int = Field(alias='pn', ge=0, le=255)
    type_port: TypePortMegaD = Field(alias='pty')
    title: str = Field(alias='emt', default='')
    name: str = Field(default='')
    device_class: str = ''

    @field_validator('type_port', mode='before')
    def convert_type_port(cls, value):
        return TypePortMegaD.get_value(value)

    @model_validator(mode='before')
    def add_name_device_class(cls, data):
        title = data.get('emt', '')
        name = title.split('/')[0]
        if name:
            data['name'] = name
        else:
            data['name'] = f'port{data["pn"]}'
        if title.count('/') > 0:
            device_class = title.split('/')[1].strip(':')
            data.update({'device_class': device_class})
        return data


class InverseValueMixin(PortConfig):
    """Добавляет функционал инверсии значения порта для НА"""

    inverse: bool = False

    @model_validator(mode='before')
    def add_inverse(cls, data):
        title = data.get('emt', '')
        if title.count('/') > 1:
            inverse = title.split('/')[2]
            data.update({'inverse': inverse})
        return data

    @field_validator('inverse', mode='before')
    def set_inverse(cls, value):
        match value:
            case '1':
                return True
            case _:
                return False


class ActionPortMixin:
    """Конфигурация действия порта"""

    action: str = Field(alias='ecmd', default='')
    execute_action: bool = Field(alias='af', default=False)
    net_action: str = Field(alias='eth', default='')
    execute_net_action: TypeNetActionMegaD = Field(
        alias='naf', default=TypeNetActionMegaD.D
    )

    @field_validator('execute_action', mode='before')
    def convert_execute_action(cls, value):
        match value:
            case 'on' | '1' | 1:
                return True
            case '':
                return False

    @field_validator('execute_net_action', mode='before')
    def convert_execute_net_action(cls, value):
        if value == '':
            return TypeNetActionMegaD.D
        return TypeNetActionMegaD.get_value(value)


class BinaryDeviceClassMixin:
    """Валидация класса бинарного устройства из поля Title"""

    @field_validator('device_class', mode='before')
    def set_device_class(cls, value):
        match value:
            case DeviceClassBinary.DOOR.value:
                return DeviceClassBinary.DOOR
            case DeviceClassBinary.GARAGE_DOOR.value:
                return DeviceClassBinary.GARAGE_DOOR
            case DeviceClassBinary.LOCK.value:
                return DeviceClassBinary.LOCK
            case DeviceClassBinary.MOISTURE.value:
                return DeviceClassBinary.MOISTURE
            case DeviceClassBinary.MOTION.value:
                return DeviceClassBinary.MOTION
            case DeviceClassBinary.SMOKE.value:
                return DeviceClassBinary.SMOKE
            case DeviceClassBinary.WINDOW.value:
                return DeviceClassBinary.WINDOW
            case _:
                return DeviceClassBinary.NONE


class PortInConfig(InverseValueMixin, ActionPortMixin, BinaryDeviceClassMixin):
    """Конфигурация портов цифровых входов"""

    mode: ModeInMegaD = Field(alias='m')
    always_send_to_server: bool = Field(alias='misc', default=False)
    device_class: DeviceClassBinary = DeviceClassBinary.NONE

    @field_validator('mode', mode='before')
    def convert_mode(cls, value):
        return ModeInMegaD.get_value(value)

    @field_validator('always_send_to_server', mode='before')
    def convert_always_send_to_server(cls, value):
        match value:
            case 'on' | '1':
                return True
            case _:
                return False


class PortOutConfig(PortConfig):
    """Конфигурация портов выходов"""

    default_value: bool = Field(alias='d', default=False)
    group: int | None = Field(alias='grp', default=None)
    mode: ModeOutMegaD = Field(alias='m')

    @field_validator('default_value', mode='before')
    def parse_default_value(cls, value):
        match value:
            case '1':
                return True
            case _:
                return False

    @field_validator('group', mode='before')
    def validate_group(cls, value):
        try:
            value = int(value)
        except ValueError:
            return None
        return value

    @field_validator('mode', mode='before')
    def convert_mode(cls, value):
        return ModeOutMegaD.get_value(value)


class DeviceClassRelayMixin:
    """Добавляет класс устройства для релейных выходов"""

    device_class: DeviceClassControl = DeviceClassControl.SWITCH

    @field_validator('device_class', mode='before')
    def set_device_class(cls, value):
        match value:
            case DeviceClassControl.SWITCH.value:
                return DeviceClassControl.SWITCH
            case DeviceClassControl.LIGHT.value:
                return DeviceClassControl.LIGHT
            case DeviceClassControl.FAN.value:
                return DeviceClassControl.FAN
            case _:
                return DeviceClassControl.SWITCH


class PortOutRelayConfig(
    DeviceClassRelayMixin, PortOutConfig, InverseValueMixin):
    """Релейный выход"""


class DeviceClassPWMMixin:
    """Добавляет класс устройства для релейных выходов"""

    device_class: DeviceClassControl = DeviceClassControl.LIGHT

    @field_validator('device_class', mode='before')
    def set_device_class(cls, value):
        match value:
            case DeviceClassControl.LIGHT.value:
                return DeviceClassControl.LIGHT
            case DeviceClassControl.FAN.value:
                return DeviceClassControl.FAN
            case _:
                return DeviceClassControl.LIGHT


class PortOutPWMConfig(DeviceClassPWMMixin, PortOutConfig):
    """ШИМ выход"""

    smooth: bool = Field(alias='misc', default=False)
    smooth_long: int = Field(alias='m2', default=0, ge=0, le=255)
    default_value: int = Field(alias='d', default=0, ge=0, le=255)
    min_value: int = Field(alias='pwmm', default=0, ge=0, le=255)
    inverse: bool = False

    @field_validator('smooth', mode='before')
    def parse_default_on(cls, value):
        match value:
            case 'on':
                return True
            case _:
                return False


class FilterSensorMixin:
    """filter"""

    filter: bool = Field(default=False)

    @model_validator(mode='before')
    def add_filter(cls, data):
        title = data.get('emt', '')
        data.update({'filter': False})
        if title.count('/') > 0:
            device_class = title.split('/')[1]
            if device_class:
                if device_class[-1] == ':':
                    data.update({'filter': True})
        return data


class ClimateDeviceClassMixin:
    """device class mixin"""

    device_class: DeviceClassClimate = DeviceClassClimate.HOME

    @field_validator('device_class', mode='before')
    def set_device_class(cls, value):
        match value:
            case DeviceClassClimate.HOME.value:
                return DeviceClassClimate.HOME
            case DeviceClassClimate.BOILER.value:
                return DeviceClassClimate.BOILER
            case DeviceClassClimate.CELLAR.value:
                return DeviceClassClimate.CELLAR
            case DeviceClassClimate.FLOOR.value:
                return DeviceClassClimate.FLOOR
            case DeviceClassClimate.OUTSIDE.value:
                return DeviceClassClimate.OUTSIDE
            case _:
                return DeviceClassClimate.HOME


class PortSensorConfig(ClimateDeviceClassMixin, PortConfig, FilterSensorMixin):
    """Конфигурация портов для сенсоров"""

    type_sensor: TypeDSensorMegaD = Field(alias='d')

    @field_validator('type_sensor', mode='before')
    def convert_type_sensor(cls, value):
        return TypeDSensorMegaD.get_value(value)


class ModeControlSensorMixin(ActionPortMixin):
    """
    Режим работы сенсора по порогу выполнения команды.
    Выбор режима доступен у 1 wire термометра и аналогово сенсора
    """

    mode: ModeSensorMegaD = Field(alias='m')
    set_value: float = Field(alias='misc', default=0.0)
    set_hst: float = Field(alias='hst', default=0.0)

    @field_validator('mode', mode='before')
    def convert_mode(cls, value):
        return ModeSensorMegaD.get_value(value)

    @field_validator('set_value', mode='before')
    def convert_set_value(cls, value):
        if type(value) is str:
            return 0.0
        return value


class OneWireSensorConfig(
    PortSensorConfig, ModeControlSensorMixin, InverseValueMixin):
    """Сенсор температурный 1 wire"""


class OneWireBusSensorConfig(PortSensorConfig):
    """Сенсоры температурные 1 wire соединённые шиной"""


class DHTSensorConfig(PortSensorConfig):
    """Сенсор температуры и влажности типа dht11, dht22"""


class IButtonConfig(PortSensorConfig, ActionPortMixin):
    """Считыватель 1-wire"""


class WiegandConfig(PortSensorConfig):
    """Считыватель Wiegand-26"""

    mode: ModeWiegandMegaD = Field(alias='m')

    @field_validator('mode', mode='before')
    def convert_mode(cls, value):
        return ModeWiegandMegaD.get_value(value)


class WiegandD0Config(WiegandConfig, ActionPortMixin):
    """Считыватель Wiegand-26 порт D0"""

    d1: int = Field(alias='misc', default=0, ge=0, le=255)


class I2CConfig(ClimateDeviceClassMixin, PortConfig, FilterSensorMixin):
    """Конфигурация порта для устройств I2C"""

    mode: ModeI2CMegaD = Field(alias='m')
    frequency: int | None = Field(alias='hst', default=None)

    @field_validator('mode', mode='before')
    def convert_mode(cls, value):
        return ModeI2CMegaD.get_value(value)


class I2CSDAConfig(I2CConfig):
    """Конфигурация порта для устройств I2C"""

    scl: int = Field(alias='misc', default=0, ge=0, le=255)
    category: CategoryI2CMegaD | str = Field(alias='gr', default='')
    device: DeviceI2CMegaD = Field(alias='d', default=DeviceI2CMegaD.NC)
    interrupt: int | None = Field(alias='inta', default=None)

    @field_validator('category', mode='before')
    def convert_category(cls, value):
        return CategoryI2CMegaD.get_value(value)

    @field_validator('device', mode='before')
    def convert_device(cls, value):
        return DeviceI2CMegaD.get_value(value)

    @field_validator('interrupt', mode='before')
    def validate_interrupt(cls, value):
        try:
            value = int(value)
        except ValueError:
            return None
        return value


class AnalogPortConfig(PortConfig, ModeControlSensorMixin):
    """Конфигурация аналогового порта"""


class ExtraPortConfig(BaseModel):
    """Базовый класс для всех портов расширителя I2C"""

    id: int = Field(alias='ext', ge=0, le=255)
    base_port: int = Field(alias='pt', ge=0, le=255)
    title: str = Field(alias='ept', default='')
    name: str = Field(default='')

    @model_validator(mode='before')
    def add_name(cls, data):
        title = data.get('ept', '')
        name = title.split('/')[0]
        if name:
            data['name'] = name
        else:
            data['name'] = f'port{data["pt"]}_ext{data["ext"]}'
        return data


class ExtraDeviceClassConfig(ExtraPortConfig):
    """Добавляет поле класса устройства для НА у портов расширителя"""

    device_class: str = ''

    @model_validator(mode='before')
    def add_device_class(cls, data):
        title = data.get('ept', '')
        if title.count('/') > 0:
            device_class = title.split('/')[1]
            data.update({'device_class': device_class})
        return data


class ExtraInverseValueMixin(ExtraDeviceClassConfig):
    """
    Добавляет функционал инверсии значения порта для НА у портов расширителя
    """

    inverse: bool = False

    @model_validator(mode='before')
    def add_inverse(cls, data):
        title = data.get('ept', '')
        if title.count('/') > 1:
            inverse = title.split('/')[2]
            data.update({'inverse': inverse})
        return data

    @field_validator('inverse', mode='before')
    def set_inverse(cls, value):
        match value:
            case '1':
                return True
            case _:
                return False


class ExtraActionPortMixin:
    """Конфигурация действия порта"""

    action: str = Field(alias='eact', default='')
    execute_action: bool = Field(alias='epf', default=False)

    @field_validator('execute_action', mode='before')
    def convert_execute_action(cls, value):
        match value:
            case 'on' | '1' | 1:
                return True
            case '':
                return False


class MCP230RelayConfig(DeviceClassRelayMixin, ExtraInverseValueMixin):
    """Релейный выход модуля расширения MCP230."""


class MCP230PortInConfig(
    ExtraActionPortMixin, ExtraInverseValueMixin, BinaryDeviceClassMixin):
    """Конфигурация портов цифровых входов модуля расширения MCP230."""

    mode: ModeInMegaD = Field(alias='emode', default=ModeInMegaD.P_R)
    device_class: DeviceClassBinary = DeviceClassBinary.NONE

    @field_validator('mode', mode='before')
    def convert_mode(cls, value):
        return ModeInMegaD.get_value(value)


class PCA9685BaseConfig(ExtraInverseValueMixin):
    """Базовая конфигурация порта модуля расширения PCA9685."""

    group: int | None = Field(alias='egrp', default=None)

    @field_validator('group', mode='before')
    def validate_group(cls, value):
        try:
            value = int(value)
        except ValueError:
            return None
        return value


class PCA9685RelayConfig(DeviceClassRelayMixin, PCA9685BaseConfig):
    """Релейный выход модуля расширения PCA9685."""


class PCA9685PWMConfig(DeviceClassPWMMixin, PCA9685BaseConfig):
    """ШИМ выход модуля расширения PCA9685."""

    min_value: int = Field(alias='emin', default=1, ge=0, le=4095)
    max_value: int = Field(alias='emax', default=4095, ge=0, le=4095)
    speed: int | None = Field(alias='espd', default=None, ge=0, le=4095)
    inverse: bool = False

    @staticmethod
    def get_value(value):
        try:
            value = int(value)
        except ValueError:
            return None
        return value

    @field_validator('min_value', mode='before')
    def validate_min_value(cls, value):
        value = cls.get_value(value)
        if value is None:
            return 1
        else:
            return value

    @field_validator('max_value', mode='before')
    def validate_max_value(cls, value):
        value = cls.get_value(value)
        if value is None:
            return 4095
        else:
            return value

    @field_validator('speed', mode='before')
    def validate_speed(cls, value):
        return cls.get_value(value)


class DeviceMegaD(BaseModel):
    plc: SystemConfigMegaD
    pids: list[PIDConfig]
    ports: list
    extra_ports: list


class LatestVersionMegaD(BaseModel):
    """Класс актуальной версии ПО контроллера."""
    name: str | None = '0'
    descr: str | None = None
    short_descr: str | None = None
    link: str | None = None
    local: bool = False
