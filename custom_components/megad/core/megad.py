import logging

from .models_megad import DeviceMegaD
from homeassistant.core import HomeAssistant


_LOGGER = logging.getLogger(__name__)


class MegaD:
    """Класс контроллера MegaD"""

    def __init__(
            self,
            hass: HomeAssistant,
            data: DeviceMegaD
    ):
        pass
