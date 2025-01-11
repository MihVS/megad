import logging

from homeassistant.config_entries import ConfigEntry
from .core.server import MegadHttpView
from homeassistant.core import HomeAssistant


_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Регистрируем HTTP эндпоинт"""

    hass.http.register_view(MegadHttpView())
    return True


async def async_setup_entry(
        hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    return True
