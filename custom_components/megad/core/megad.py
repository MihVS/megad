import asyncio
import logging
from http import HTTPStatus
from typing import Union

import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .base_ports import (
    BinaryPortIn, ReleyPortOut, PWMPortOut, BinaryPortClick, BinaryPortCount,
    BasePort, OneWireSensorPort, DHTSensorPort, OneWireBusSensorPort,
    I2CSensorSCD4x, I2CSensorSTH31, AnalogSensor
)
from .config_parser import (
    get_uptime, async_get_page_config, get_temperature_megad,
    get_version_software, async_get_page_port, get_set_temp_thermostat,
    get_status_thermostat
)
from .enums import (
    TypePortMegaD, ModeInMegaD, ModeOutMegaD, TypeDSensorMegaD, DeviceI2CMegaD,
    ModeI2CMegaD, ModeSensorMegaD
)
from .exceptions import PortBusy, InvalidPasswordMegad
from .models_megad import DeviceMegaD
from ..const import (
    MAIN_CONFIG, START_CONFIG, TIME_OUT_UPDATE_DATA, PORT, COMMAND, ALL_STATES,
    LIST_STATES, SCL_PORT, I2C_DEVICE, TIME_SLEEP_REQUEST, COUNT_UPDATE,
    SET_TEMPERATURE
)

_LOGGER = logging.getLogger(__name__)


class MegaD:
    """Класс контроллера MegaD"""

    def __init__(
            self,
            hass: HomeAssistant,
            config: DeviceMegaD
    ):
        self.hass = hass
        self.session = async_get_clientsession(hass)
        self.config: DeviceMegaD = config
        self.id = config.plc.megad_id
        self.ports: list[Union[
            BinaryPortIn, BinaryPortClick, BinaryPortCount, ReleyPortOut,
            PWMPortOut, OneWireSensorPort, DHTSensorPort, OneWireBusSensorPort,
            I2CSensorSCD4x, I2CSensorSTH31, AnalogSensor
        ]] = []
        self.url = (f'http://{self.config.plc.ip_megad}/'
                    f'{self.config.plc.password}/')
        self.uptime: int = 0
        self.temperature: float = 0
        self.software: str | None = None
        self.request_count: int = COUNT_UPDATE
        self.init_ports()
        _LOGGER.debug(f'Создан объект MegaD: {self}')

    def __repr__(self):
        return (f"<MegaD(id={self.config.plc.megad_id}, "
                f"ip={self.config.plc.ip_megad}, ports={self.ports})>")

    async def get_status(self, params: dict) -> str:
        """Получение статуса по переданным параметрам"""
        response = await self.session.get(url=self.url, params=params)
        if response.status == HTTPStatus.UNAUTHORIZED:
            _LOGGER.error(f'Неверный пароль для устройства с id {self.id}')
            raise InvalidPasswordMegad(f'Проверьте пароль у устройства '
                                       f'с id {self.id}')
        return await response.text()

    async def get_status_ports(self) -> str:
        """Запрос состояния всех портов"""
        params = {COMMAND: ALL_STATES}
        text = await self.get_status(params)
        _LOGGER.debug(f'Состояние всех портов id:{self.id}: {text}')
        return text

    async def update_data(self):
        """Обновление всех данных контроллера."""

        await self.update_ports()
        if self.request_count == COUNT_UPDATE:
            self.request_count = 0
            await asyncio.sleep(TIME_SLEEP_REQUEST)
            page_cf0 = await async_get_page_config(
                START_CONFIG, self.url, self.session
            )
            self.software = get_version_software(page_cf0)
            _LOGGER.debug(f'Версия ПО контроллера id:'
                          f'{self.id}: {self.software}')
        await asyncio.sleep(TIME_SLEEP_REQUEST)
        page_cf1 = await async_get_page_config(
            MAIN_CONFIG, self.url, self.session
        )
        self.uptime = get_uptime(page_cf1)
        _LOGGER.debug(f'Время работы контроллера id:{self.id}: {self.uptime}')
        self.temperature = get_temperature_megad(page_cf1)
        _LOGGER.debug(f'Температура платы контролера '
                      f'id:{self.id}: {self.temperature}')
        self.request_count += 1

    @staticmethod
    def check_port_is_thermostat(port) -> bool:
        """Проверка является ли порт термостатом"""
        if isinstance(port, OneWireSensorPort):
            if (
                    port.conf.mode == ModeSensorMegaD.LESS_AND_MORE
                    and port.conf.execute_action
            ):
                return True
        else:
            return False

    async def update_ports(self):
        """Обновление данных настроенных портов"""
        status_ports_raw = await self.get_status_ports()
        status_ports = status_ports_raw.split(';')
        for port in self.ports:
            state = status_ports[port.conf.id]
            if self.check_port_is_thermostat(port):
                await asyncio.sleep(TIME_SLEEP_REQUEST)
                page = await async_get_page_port(
                    port.conf.id, self.url, self.session
                )
                port.status = get_status_thermostat(page)
                port.conf.set_value = get_set_temp_thermostat(page)
            if state:
                port.update_state(state)
            elif isinstance(port, OneWireBusSensorPort):
                await asyncio.sleep(TIME_SLEEP_REQUEST)
                state = await self.get_status_one_wire_bus(port)
                port.update_state(state)
            elif isinstance(port, I2CSensorSCD4x):
                await asyncio.sleep(TIME_SLEEP_REQUEST)
                state = await self.get_status_scd4x(port)
                port.update_state(state)

    async def get_status_one_wire_bus(self, port: OneWireBusSensorPort) -> str:
        """Обновление шины сенсоров порта 1 wire"""
        params = {PORT: port.conf.id, COMMAND: LIST_STATES}
        text = await self.get_status(params)
        _LOGGER.debug(f'Состояние 1 wire bus {self.id}-{port.conf.name}: '
                      f'{text}')
        return text

    async def get_status_scd4x(self, port: I2CSensorSCD4x) -> str:
        """Обновление сенсора СО2 типа SCD4x"""
        params = {
            PORT: port.conf.id,
            SCL_PORT: port.conf.scl,
            I2C_DEVICE: port.conf.device
        }
        text = await self.get_status(params)
        _LOGGER.debug(f'Состояние I2C сенсора {self.id}-{port.conf.name}: '
                      f'{text}')
        return text

    def init_ports(self):
        """Инициализация портов. Разделение их на устройства."""
        for port in self.config.ports:
            if (
                    port.type_port == TypePortMegaD.IN
                    and (port.mode == ModeInMegaD.P_R or
                         port.always_send_to_server)
            ):
                self.ports.append(BinaryPortIn(port, self.id))
            elif (
                    port.type_port == TypePortMegaD.IN
                    and port.mode == ModeInMegaD.C
            ):
                self.ports.append(BinaryPortClick(port, self.id))
            elif port.type_port == TypePortMegaD.IN:
                self.ports.append(BinaryPortCount(port, self.id))
            elif (
                    port.type_port == TypePortMegaD.OUT
                    and (port.mode in (ModeOutMegaD.SW, ModeOutMegaD.SW_LINK))
            ):
                self.ports.append(ReleyPortOut(port, self.id))
            elif (
                    port.type_port == TypePortMegaD.OUT
                    and (port.mode in (ModeOutMegaD.PWM, ))
            ):
                self.ports.append(PWMPortOut(port, self.id))
            elif port.type_port == TypePortMegaD.DSEN:
                match port.type_sensor:
                    case TypeDSensorMegaD.ONEW:
                        self.ports.append(OneWireSensorPort(port, self.id))
                    case TypeDSensorMegaD.DHT11 | TypeDSensorMegaD.DHT22:
                        self.ports.append(DHTSensorPort(port, self.id))
                    case TypeDSensorMegaD.ONEWBUS:
                        self.ports.append(OneWireBusSensorPort(port, self.id))
            elif (
                    port.type_port == TypePortMegaD.I2C
                    and port.mode == ModeI2CMegaD.SDA
            ):
                match port.device:
                    case DeviceI2CMegaD.SCD4x:
                        self.ports.append(I2CSensorSCD4x(port, self.id))
                    case DeviceI2CMegaD.SHT31:
                        self.ports.append(I2CSensorSTH31(port, self.id))
            elif port.type_port == TypePortMegaD.ADC:
                self.ports.append(AnalogSensor(port, self.id))

        _LOGGER.debug(f'Инициализированные порты: {self.ports}')

    def update_port(self, port_id, data):
        """Обновить данные порта по его id"""
        port = self.get_port(port_id)
        if port:
            old_state = port.state
            port.update_state(data)
            new_state = port.state
            self._check_change_port(port, old_state, new_state)

    def get_port(self, port_id):
        """Получить порт по его id"""
        return next(
            (port for port in self.ports
             if port.conf.id == int(port_id)),
            None
        )

    async def set_temperature(self, port_id, temperature):
        """Установка заданной температуры терморегулятора."""
        params = {PORT: port_id, SET_TEMPERATURE: temperature}
        async with async_timeout.timeout(TIME_OUT_UPDATE_DATA):
            response = await self.session.get(url=self.url, params=params)

        text = await response.text()
        match text:
            case 'busy':
                _LOGGER.warning(f'Не удалось изменить заданную температуру '
                                f'порта №{port_id} на {temperature}')
                raise PortBusy
            case _:
                _LOGGER.debug(f'Заданная температура порта №{port_id} '
                              f'изменена на {temperature}')

    async def set_port(self, port_id, command):
        """Управление выходом релейным и шим"""
        params = {COMMAND: f'{port_id}:{command}'}
        async with async_timeout.timeout(TIME_OUT_UPDATE_DATA):
            response = await self.session.get(url=self.url, params=params)

        text = await response.text()
        match text:
            case 'busy':
                _LOGGER.warning(f'Не удалось изменить состояние порта или '
                                f'группы портов №{port_id}. '
                                f'Команда: {command}')
                raise PortBusy
            case _:
                if 'g' in str(port_id):
                    _LOGGER.debug(f'Группа портов №{port_id} изменила'
                                  f' состояние на {command}')

    def _check_change_port(
            self, port: BasePort, old_state: str, new_state: str) -> bool:
        """Проверяет новое и старое состояния портов."""

        if old_state != new_state:
            _LOGGER.debug(f'Порт №{port.conf.id} - {port.conf.name}, '
                          f'устройства id:{self.id}, '
                          f'изменил состояние с {old_state} на {new_state}')
            return True
        return False
