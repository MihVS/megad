import logging
from typing import Union

from .base_ports import BinaryPortIn, ReleyPortOut, PWMPortOut
from .enums import TypePortMegaD, ModeInMegaD
from .models_megad import DeviceMegaD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession


_LOGGER = logging.getLogger(__name__)


class MegaD:
    """Класс контроллера MegaD"""

    def __init__(
            self,
            hass: HomeAssistant,
            config: DeviceMegaD
    ):
        self.session = async_get_clientsession(hass)
        self.config: DeviceMegaD = config
        self.ports: list[Union[BinaryPortIn, ReleyPortOut, PWMPortOut]] = []
        self.url = (f'http://{self.config.plc.ip_megad}/'
                    f'{self.config.plc.password}/')
        _LOGGER.debug(f'Создан объект MegaD: {self}')

    def __repr__(self):
        return (f"<MegaD(id={self.config.plc.megad_id}, "
                f"ip={self.config.plc.ip_megad}, ports={self.ports})>")

    async def get_status_ports(self) -> str:
        """Запрос состояния всех портов"""
        params = {'cmd': 'all'}
        response = await self.session.get(url=self.url, params=params)
        text = await response.text()
        _LOGGER.debug(f'Состояние всех портов: {text}')
        return text

    async def update_ports(self):
        """Инициализация портов"""
        status_ports_raw = await self.get_status_ports()
        status_ports = status_ports_raw.split(';')
        for port in self.config.ports:
            if (
                    port.type_port == TypePortMegaD.IN
                    and (port.mode == ModeInMegaD.P_R or
                         port.always_send_to_server)
            ):
                binary_sensor = BinaryPortIn(port)
                binary_sensor.update_state(status_ports[port.id])
                self.ports.append(binary_sensor)



