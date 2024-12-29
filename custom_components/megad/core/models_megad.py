from ipaddress import IPv4Address
from typing import Union
from urllib.parse import unquote, quote

from pydantic import BaseModel, Field, field_validator, model_validator

from .enums import (ServerTypeMegaD, ConfigUARTMegaD, TypeNetActionMegaD,
                    TypePortMegaD, ModeInMegaD, DeviceClassBinary,
                    ModeOutMegaD, DeviceClassControl, TypeDSensorMegaD,
                    ModeSensorMegaD, ModeWiegandMegaD, ModeI2CMegaD,
                    CategoryI2CMegaD, DeviceI2CMegaD)


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
        return ConfigUARTMegaD.get_value(value)


class PortMegaD(BaseModel):
    """Базовый класс для всех портов"""

    id: int = Field(alias='pn', ge=0, le=255)
    type_port: TypePortMegaD = Field(alias='pty')
    title: str = Field(alias='emt', default='')
    name: str = Field(default='')

    @field_validator('title', mode='before')
    def decode_title(cls, value):
        return unquote(value).encode('latin1').decode('windows-1251')

    @field_validator('type_port', mode='before')
    def convert_type_port(cls, value):
        return TypePortMegaD.get_value(value)

    @model_validator(mode='before')
    def add_name(cls, data):
        title = data.get('emt', '')
        decoded_title = unquote(title).encode('latin1').decode('windows-1251')
        name = decoded_title.split('/')[0]
        if name:
            data['name'] = name
        else:
            data['name'] = f'port{data["pn"]}'
        return data


class DeviceClassMegaD(PortMegaD):
    """Добавляет поле класса устройства для НА"""

    device_class: str = ''

    @model_validator(mode='before')
    def add_device_class(cls, data):
        title = data.get('emt')
        decoded_title = unquote(title).encode('latin1').decode('windows-1251')
        if decoded_title.count('/') > 0:
            device_class = decoded_title.split('/')[1]
            data.update({'device_class': device_class})
        return data


class InverseValueMixin:
    """Добавляет функционал инверсии значения порта для НА"""

    inverse: bool = False

    @model_validator(mode='before')
    def add_device_class(cls, data):
        title = data.get('emt')
        decoded_title = unquote(title).encode('latin1').decode('windows-1251')
        if decoded_title.count('/') > 1:
            inverse = decoded_title.split('/')[2]
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

    @field_validator('action')
    def decode_action(cls, value):
        return unquote(value)

    @field_validator('execute_action', mode='before')
    def convert_execute_action(cls, value):
        match value:
            case 'on':
                return True
            case '':
                return False

    @field_validator('net_action')
    def decode_net_action(cls, value):
        return unquote(value)

    @field_validator('execute_net_action', mode='before')
    def convert_execute_net_action(cls, value):
        return TypeNetActionMegaD.get_value(value)


class PortInMegaD(DeviceClassMegaD, InverseValueMixin, ActionPortMixin):
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
            case 'door':
                return DeviceClassBinary.DOOR
            case 'garage_door':
                return DeviceClassBinary.GARAGE_DOOR
            case 'lock':
                return DeviceClassBinary.LOCK
            case 'moisture':
                return DeviceClassBinary.MOISTURE
            case 'motion':
                return DeviceClassBinary.MOTION
            case 'smoke':
                return DeviceClassBinary.SMOKE
            case 'window':
                return DeviceClassBinary.WINDOW
            case _:
                return DeviceClassBinary.NONE


class PortOutMegaD(DeviceClassMegaD):
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


class PortOutRelayMegaD(PortOutMegaD, InverseValueMixin):
    """Релейный выход"""

    device_class: DeviceClassControl = DeviceClassControl.SWITCH

    @field_validator('device_class', mode='before')
    def set_device_class(cls, value):
        match value:
            case 'switch':
                return DeviceClassControl.SWITCH
            case 'light':
                return DeviceClassControl.LIGHT
            case 'fan':
                return DeviceClassControl.FAN
            case _:
                return DeviceClassControl.SWITCH


class PortOutPWMMegaD(PortOutMegaD):
    """ШИМ выход"""

    device_class: DeviceClassControl = DeviceClassControl.LIGHT
    smooth: bool = Field(alias='misc', default=False)
    smooth_long: int = Field(alias='m2', default=0, ge=0, le=255)
    default_value: int = Field(alias='d', default=0, ge=0, le=255)
    min_value: int = Field(alias='pwmm', default=0, ge=0, le=255)

    @field_validator('device_class', mode='before')
    def set_device_class(cls, value):
        match value:
            case 'light':
                return DeviceClassControl.LIGHT
            case 'fan':
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


class PortSensorMegaD(PortMegaD):
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


class OneWireSensorMegaD(PortSensorMegaD, ModeControlSensorMixin):
    """Сенсор температурный 1 wire"""


class DHTSensorMegaD(PortSensorMegaD):
    """Сенсор температуры и влажности типа dht11, dht22"""


class IButtonMegaD(PortSensorMegaD, ActionPortMixin):
    """Считыватель 1-wire"""


class WiegandMegaD(PortSensorMegaD):
    """Считыватель Wiegand-26"""

    mode: ModeWiegandMegaD = Field(alias='m')

    @field_validator('mode', mode='before')
    def convert_mode(cls, value):
        return ModeWiegandMegaD.get_value(value)


class WiegandD0MegaD(WiegandMegaD, ActionPortMixin):
    """Считыватель Wiegand-26 порт D0"""

    d1: int = Field(alias='misc', default=0, ge=0, le=255)


class I2CMegaD(PortMegaD):
    """Конфигурация порта для устройств I2C"""

    mode: ModeI2CMegaD = Field(alias='m')

    @field_validator('mode', mode='before')
    def convert_mode(cls, value):
        return ModeI2CMegaD.get_value(value)


class I2CSDAMegaD(I2CMegaD):
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


class AnalogPortMegaD(PortMegaD, ModeControlSensorMixin):
    """Конфигурация аналогового порта"""


class DeviceMegaD(BaseModel):
    plc: SystemConfigMegaD
    ports: list[Union[
        PortMegaD, PortInMegaD, PortOutMegaD, PortOutRelayMegaD,
        PortOutPWMMegaD, PortSensorMegaD, OneWireSensorMegaD, DHTSensorMegaD,
        IButtonMegaD, WiegandMegaD, WiegandD0MegaD, I2CMegaD, I2CSDAMegaD,
        AnalogPortMegaD
    ]]
