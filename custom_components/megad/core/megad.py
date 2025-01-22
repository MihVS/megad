import logging
from typing import Union

import async_timeout
from http import HTTPStatus

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .base_ports import (
    BinaryPortIn, ReleyPortOut, PWMPortOut, BinaryPortClick, BinaryPortCount,
    BasePort
)
from .config_parser import (
    get_uptime, async_get_page_config, get_temperature_megad,
    get_version_software
)
from .enums import TypePortMegaD, ModeInMegaD, ModeOutMegaD
from .exceptions import PortBusy, InvalidPasswordMegad
from .models_megad import DeviceMegaD
from ..const import MAIN_CONFIG, START_CONFIG, TIME_OUT_UPDATE_DATA

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
            PWMPortOut
        ]] = []
        self.url = (f'http://{self.config.plc.ip_megad}/'
                    f'{self.config.plc.password}/')
        self.uptime: int = 0
        self.temperature: float = 0
        self.software: str | None = None
        self.init_ports()
        _LOGGER.debug(f'Создан объект MegaD: {self}')

    def __repr__(self):
        return (f"<MegaD(id={self.config.plc.megad_id}, "
                f"ip={self.config.plc.ip_megad}, ports={self.ports})>")

    async def get_status_ports(self) -> str:
        """Запрос состояния всех портов"""
        params = {'cmd': 'all'}
        response = await self.session.get(url=self.url, params=params)
        if response.status == HTTPStatus.UNAUTHORIZED:
            _LOGGER.error(f'Неверный пароль для устройства с id {self.id}')
            raise InvalidPasswordMegad(f'Проверьте пароль у устройства '
                                       f'с id {self.id}')
        text = await response.text()
        _LOGGER.debug(f'Состояние всех портов id:{self.id}: {text}')
        return text

    async def update_data(self):
        """Обновление всех данных контроллера."""

        await self.update_ports()
        page_cf0 = await async_get_page_config(
            START_CONFIG, self.url, self.session
        )
        page_cf1 = await async_get_page_config(
            MAIN_CONFIG, self.url, self.session
        )
        self.uptime = get_uptime(page_cf1)
        self.temperature = get_temperature_megad(page_cf1)
        self.software = get_version_software(page_cf0)

    async def update_ports(self):
        """Обновление данных настроенных портов"""

        status_ports_raw = await self.get_status_ports()
        status_ports = status_ports_raw.split(';')
        for port in self.ports:
            state = status_ports[port.conf.id]
            if state:
                port.update_state(state)

    def init_ports(self):
        """Инициализация портов. Разделение их на устройства."""

        for port in self.config.ports:
            if (
                    port.type_port == TypePortMegaD.IN
                    and (port.mode == ModeInMegaD.P_R or
                         port.always_send_to_server)
            ):
                binary_sensor = BinaryPortIn(port)
                self.ports.append(binary_sensor)
            elif (
                    port.type_port == TypePortMegaD.IN
                    and port.mode == ModeInMegaD.C
            ):
                button = BinaryPortClick(port)
                self.ports.append(button)
            elif port.type_port == TypePortMegaD.IN:
                count = BinaryPortCount(port)
                self.ports.append(count)
            elif (
                    port.type_port == TypePortMegaD.OUT
                    and (port.mode in (ModeOutMegaD.SW, ModeOutMegaD.SW_LINK))
            ):
                relay = ReleyPortOut(port)
                self.ports.append(relay)
            elif (
                    port.type_port == TypePortMegaD.OUT
                    and (port.mode in (ModeOutMegaD.PWM, ))
            ):
                pwm = PWMPortOut(port)
                self.ports.append(pwm)

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

    async def set_port(self, port_id, command):
        """Управление выходом релейным и шим"""

        params = {'cmd': f'{port_id}:{command}'}
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
