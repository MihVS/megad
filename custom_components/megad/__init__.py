import logging

from homeassistant.config_entries import ConfigEntry
from .core.config_parser import create_config_megad
from .core.megad import MegaD
from .core.server import MegadHttpView
from homeassistant.core import HomeAssistant


_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Регистрируем HTTP ручку"""

    hass.http.register_view(MegadHttpView())
    return True


async def async_setup_entry(
        hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    megad_config = hass.data.get('megad_config')
    megad = MegaD(hass=hass, config=megad_config)
    await megad.update_ports()
    _LOGGER.debug(megad)

    return True
