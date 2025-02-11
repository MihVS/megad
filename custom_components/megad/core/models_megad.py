from ipaddress import IPv4Address
from typing import Union
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
    server_type: ServerTypeMegaD = Field(alias='srvt')
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


class AddNameMixin:
    """Добавляет название устройства из Title"""

    name: str = Field(default='')

    @model_validator(mode='before')
    def add_name(cls, data):
        title = data.get('pidt', '')
        name = title.split('/')[0]
        if name:
            data['name'] = name
        else:
            data['name'] = f'port{data["pn"]}'
        return data


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

    @field_validator('type_port', mode='before')
    def convert_type_port(cls, value):
        return TypePortMegaD.get_value(value)

    @model_validator(mode='before')
    def add_name(cls, data):
        title = data.get('emt', '')
        name = title.split('/')[0]
        if name:
            data['name'] = name
        else:
            data['name'] = f'port{data["pn"]}'
        return data


class DeviceClassConfig(PortConfig):
    """Добавляет поле класса устройства для НА"""

    device_class: str = ''

    @model_validator(mode='before')
    def add_device_class(cls, data):
        title = data.get('emt', '')
        if title.count('/') > 0:
            device_class = title.split('/')[1]
            data.update({'device_class': device_class})
        return data


class InverseValueMixin(DeviceClassConfig):
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
        return TypeNetActionMegaD.get_value(value)


class PortInConfig(InverseValueMixin, ActionPortMixin):
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
            case 'on':
                return True
            case _:
                return False

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


class PortOutConfig(DeviceClassConfig):
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


class PortOutRelayConfig(PortOutConfig, InverseValueMixin):
    """Релейный выход"""

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


class PortOutPWMConfig(PortOutConfig):
    """ШИМ выход"""

    device_class: DeviceClassControl = DeviceClassControl.LIGHT
    smooth: bool = Field(alias='misc', default=False)
    smooth_long: int = Field(alias='m2', default=0, ge=0, le=255)
    default_value: int = Field(alias='d', default=0, ge=0, le=255)
    min_value: int = Field(alias='pwmm', default=0, ge=0, le=255)
    inverse: bool = False

    @field_validator('device_class', mode='before')
    def set_device_class(cls, value):
        match value:
            case DeviceClassControl.LIGHT.value:
                return DeviceClassControl.LIGHT
            case DeviceClassControl.FAN.value:
                return DeviceClassControl.FAN
            case _:
                return DeviceClassControl.LIGHT

    @field_validator('smooth', mode='before')
    def parse_default_on(cls, value):
        match value:
            case 'on':
                return True
            case _:
                return False


class PortSensorConfig(PortConfig):
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


class OneWireSensorConfig(
    PortSensorConfig, ModeControlSensorMixin, InverseValueMixin):
    """Сенсор температурный 1 wire"""

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
            case _:
                return DeviceClassClimate.HOME


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


class I2CConfig(PortConfig):
    """Конфигурация порта для устройств I2C"""

    mode: ModeI2CMegaD = Field(alias='m')

    @field_validator('mode', mode='before')
    def convert_mode(cls, value):
        return ModeI2CMegaD.get_value(value)


class I2CSDAConfig(I2CConfig):
    """Конфигурация порта для устройств I2C"""

    scl: int = Field(alias='misc', default=0, ge=0, le=255)
    category: CategoryI2CMegaD | str = Field(alias='gr', default='')
    device: DeviceI2CMegaD = Field(alias='d', default=DeviceI2CMegaD.NC)

    @field_validator('category', mode='before')
    def convert_category(cls, value):
        return CategoryI2CMegaD.get_value(value)

    @field_validator('device', mode='before')
    def convert_device(cls, value):
        return DeviceI2CMegaD.get_value(value)


class AnalogPortConfig(PortConfig, ModeControlSensorMixin):
    """Конфигурация аналогового порта"""


class DeviceMegaD(BaseModel):
    plc: SystemConfigMegaD
    pids: list[PIDConfig] = []
    ports: list[Union[
        PortConfig, PortInConfig, PortOutConfig, PortOutRelayConfig,
        PortOutPWMConfig, PortSensorConfig, OneWireSensorConfig,
        DHTSensorConfig, IButtonConfig, WiegandConfig, WiegandD0Config,
        I2CConfig, I2CSDAConfig, AnalogPortConfig
    ]]
