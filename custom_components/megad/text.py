import asyncio
import logging

from propcache import cached_property

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from . import MegaDCoordinator
from .const import DOMAIN, ENTRIES, CURRENT_ENTITY_IDS, PORT, DISPLAY_COMMAND
from .core.base_ports import I2CDisplayPort
from .core.megad import MegaD

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback
) -> None:
    entry_id = config_entry.entry_id
    coordinator = hass.data[DOMAIN][ENTRIES][entry_id]
    megad = coordinator.megad

    displays = []

    for port in megad.ports:
        if isinstance(port, I2CDisplayPort):
            unique_id = f'{entry_id}-{megad.id}-{port.conf.id}-display'
            displays.append(MegaDDisplayEntity(coordinator, port, unique_id))

    for display in displays:
        hass.data[DOMAIN][CURRENT_ENTITY_IDS][entry_id].append(
            display.unique_id)
    if displays:
        async_add_entities(displays)
        _LOGGER.debug(f'Добавлены дисплеи: {displays}')


class MegaDDisplayEntity(CoordinatorEntity, TextEntity):
    """Класс текстового поля для дисплеев."""

    def __init__(
            self, coordinator: MegaDCoordinator, port: I2CDisplayPort,
            unique_id: str
    ):
        """Инициализация."""
        super().__init__(coordinator)
        self._coordinator: MegaDCoordinator = coordinator
        self._megad: MegaD = coordinator.megad
        self._port: I2CDisplayPort = port
        self._name: str = port.conf.name
        self._unique_id = unique_id
        self.entity_id = (f'text.{self._megad.id}_port{port.conf.id}_'
                          f'{port.conf.device.value}')
        self._attr_device_info = coordinator.devices_info()

    def __repr__(self) -> str:
        if not self.hass:
            return f"<Sensor entity {self.entity_id}>"
        return super().__repr__()

    @cached_property
    def name(self) -> str:
        return self._name

    @cached_property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def native_value(self) -> str:
        """Возвращает состояние сенсора"""
        return self._port.state

    def clean_line(self) -> dict:
        raise NotImplementedError

    def write_line(self, line: str) -> dict:
        raise NotImplementedError

    async def async_set_value(self, value: str) -> None:
        """Set the text value."""
        _LOGGER.debug(f'Текст переданный на дисплей: {value}')
        await self._megad.request_to_megad(self.clean_line())
        await asyncio.sleep(0.2)
        await self._megad.request_to_megad(self.write_line(value))


class DisplayLCD1602(MegaDDisplayEntity):

    def clean_line(self) -> dict:
        return {PORT: self._port.conf.id, DISPLAY_COMMAND: 1}

