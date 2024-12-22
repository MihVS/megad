import logging

from homeassistant.core import HomeAssistant


_LOGGER = logging.getLogger(__name__)


class MegaD:
    """Класс контроллера MegaD"""

    def __init__(
            self,
            hass: HomeAssistant,
            host: str,
            name: str,
            password: str,
    ):
        pass
