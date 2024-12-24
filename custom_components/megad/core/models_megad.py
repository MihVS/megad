from ipaddress import IPv4Address
from urllib.parse import unquote, quote

from pydantic import BaseModel, Field, validator

from .enums import (
    ServerTypeMegaD, ConfigUARTMegaD, TypeNetActionMegaD, TypePortMegaD,
    ModeInMegaD, DeviceClassBinary, ModeOutMegaD, DeviceClassControl,
    TypeDSensorMegaD
)


class SystemConfigMegaD(BaseModel):
    """Главный конфиг контроллера"""

    ip_megad: IPv4Address = Field(alias='eip')
    network_mask: IPv4Address = Field(alias='emsk', default=None)
    password: str = Field(alias='pwd', max_length=3)
    gateway: IPv4Address = Field(alias='gw')
    ip_server: str = Field(alias='sip')
    server_type: ServerTypeMegaD = Field(alias='srvt')
    slug: str = Field(alias='sct')
    uart: ConfigUARTMegaD = Field(alias='gsm')


    @validator('password')
    def validate_password_length(cls, value):
        if len(value) > 3:
            raise ValueError(
                'The password must contain no more than 3 characters.'
            )
        return value

    @validator('ip_server', pre=True)
    def decode_ip_and_port(cls, value):
        decoded_value = unquote(value)
        ip, port = decoded_value.split(':')
        IPv4Address(ip)
        return decoded_value

    @validator('server_type', pre=True)
    def convert_server_type(cls, value):
        return ServerTypeMegaD.get_value(value)

    @validator('uart', pre=True)
    def convert_uart_type(cls, value):
        return ConfigUARTMegaD.get_value(value)

class PortMegaD(BaseModel):
    """Базовый класс для всех портов"""

    id: int = Field(alias='pn', ge=0, le=255)
    type_port: TypePortMegaD = Field(alias='pty')
    title: str = Field(alias='emt', default='')
    inverse: bool = False
    value: str = 'OFF'

    @validator('type_port', pre=True)
    def convert_type_port(cls, value):
        return TypePortMegaD.get_value(value)

    @validator('title', pre=True)
    def parse_title(cls, value, values):
        if quote('|') in value:
            device_class, inverse = value.split(quote('|'))
            values.update({'device_class': device_class})
            values.update({'inverse': inverse})
        else:
            values.update({'device_class': value})
        return unquote(value)

    @validator('inverse', always=True)
    def set_inverse(cls, value, values):
        inverse = values.get('inverse', value)
        match inverse:
            case 'true':
                return True
            case _:
                return False


class PortInMegaD(PortMegaD):
    """Конфигурация портов цифровых входов"""

    action: str = Field(alias='ecmd')
    execute_action: bool = Field(alias='af', default=False)
    net_action: str = Field(alias='eth')
    execute_net_action: TypeNetActionMegaD = Field(alias='naf')
    mode: ModeInMegaD = Field(alias='m')
    always_send_to_server: bool = Field(alias='misc', default=False)
    device_class: DeviceClassBinary = DeviceClassBinary.NONE

    @validator('action')
    def decode_action(cls, value):
        return unquote(value)

    @validator('execute_action', pre=True)
    def convert_execute_action(cls, value):
        match value:
            case 'on':
                return True
            case '':
                return False

    @validator('net_action')
    def decode_net_action(cls, value):
        return unquote(value)

    @validator('execute_net_action', pre=True)
    def convert_execute_net_action(cls, value):
        return TypeNetActionMegaD.get_value(value)

    @validator('mode', pre=True)
    def convert_mode(cls, value):
        return ModeInMegaD.get_value(value)

    @validator('always_send_to_server', pre=True)
    def convert_always_send_to_server(cls, value):
        match value:
            case 'on':
                return True
            case _:
                return False

    @validator('device_class', always=True)
    def set_device_class(cls, value, values):
        device_class = values.get('device_class', value)
        match device_class:
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


class PortOutMegaD(PortMegaD):
    """Конфигурация портов выходов"""

    default_value: bool = Field(alias='d', default=False)
    group: int | None = Field(alias='grp', default=None)
    mode: ModeOutMegaD = Field(alias='m')

    @validator('default_value', pre=True)
    def parse_default_value(cls, value):
        match value:
            case '1':
                return True
            case _:
                return False

    @validator('group', pre=True)
    def validate_group(cls, value):
        try:
            value = int(value)
        except ValueError:
            return None
        return value

    @validator('mode', pre=True)
    def convert_mode(cls, value):
        return ModeOutMegaD.get_value(value)


class PortOutRelayMegaD(PortOutMegaD):
    """Релейный выход"""

    device_class: DeviceClassControl = DeviceClassControl.SWITCH

    @validator('device_class', always=True)
    def set_device_class(cls, value, values):
        device_class = values.get('device_class', value)
        match device_class:
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

    value: int = Field(default=0, ge=0, le=255)
    device_class: DeviceClassControl = DeviceClassControl.LIGHT
    smooth: bool = Field(alias='misc', default=False)
    smooth_long: int = Field(alias='m2', default=0, ge=0, le=255)
    default_value: int = Field(alias='d', default=0, ge=0, le=255)
    min_value: int = Field(alias='pwmm', default=0, ge=0, le=255)

    @validator('device_class', always=True)
    def set_device_class(cls, value, values):
        device_class = values.get('device_class', value)
        match device_class:
            case 'light':
                return DeviceClassControl.LIGHT
            case 'fan':
                return DeviceClassControl.FAN
            case _:
                return DeviceClassControl.LIGHT

    @validator('smooth', pre=True)
    def parse_default_on(cls, value):
        match value:
            case 'on':
                return True
            case _:
                return False


class PortSensorMegaD(PortMegaD):
    """Конфигурация портов для сенсоров"""

    value: str = ''
    type_sensor: TypeDSensorMegaD = Field(alias='d')

    @validator('type_sensor', pre=True)
    def convert_type_sensor(cls, value):
        return TypeDSensorMegaD.get_value(value)


class DeviceMegaD(BaseModel):
    controller: SystemConfigMegaD
    binary_sensors: list[PortInMegaD] = []
    relay_outs: list[PortOutRelayMegaD] = []
    pwm_outs: list[PortOutPWMMegaD] = []
