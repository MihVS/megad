import logging

from propcache import cached_property

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass, BinarySensorEntity
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from . import MegaDCoordinator
from .const import DOMAIN, PORT_COMMAND
from .core.base_ports import ReleyPortOut
from .core.enums import DeviceClassBinary, DeviceClassControl
from .core.megad import MegaD

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback
) -> None:
    entry_id = config_entry.entry_id
    coordinator = hass.data[DOMAIN][entry_id]
    megad = coordinator.megad

    switches = []
    for port in megad.ports:
        if isinstance(port, ReleyPortOut):
            if port.conf.device_class == DeviceClassControl.SWITCH:
                unique_id = f'{entry_id}-{megad.id}-{port.conf.id}'
                switches.append(SwitchMegaD(
                    coordinator, port, unique_id)
                )
    if switches:
        async_add_entities(switches)
        _LOGGER.debug(f'Добавлены переключатели: {switches}')


class SwitchMegaD(CoordinatorEntity, BinarySensorEntity):

    def __init__(
            self, coordinator: MegaDCoordinator, port: ReleyPortOut,
            unique_id: str
    ) -> None:
        super().__init__(coordinator)
        self._megad: MegaD = coordinator.megad
        self._port: ReleyPortOut = port
        self._switch_name: str = port.conf.name
        self._unique_id: str = unique_id
        self._attr_device_info = coordinator.devices_info()
        self.entity_id = f'switch.{self._megad.id}_port{port.conf.id}'

    def __repr__(self) -> str:
        if not self.hass:
            return f"<Switch entity {self.entity_id}>"
        return super().__repr__()

    @cached_property
    def name(self) -> str:
        return self._switch_name

    @cached_property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self._port.state

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        await self._megad.set_port(self._port.conf.id, PORT_COMMAND.ON)

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await self._megad.set_port(self._port.conf.id, PORT_COMMAND.OFF)

    async def async_toggle(self, **kwargs):
        """Toggle the entity."""
        await self._megad.set_port(self._port.conf.id, PORT_COMMAND.TOGGLE)
