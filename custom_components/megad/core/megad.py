import logging

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
        self.config = config
