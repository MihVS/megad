import logging

from propcache import cached_property

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from . import MegaDCoordinator
from .const import DOMAIN, PORT_COMMAND
from .core.base_ports import ReleyPortOut, PWMPortOut
from .core.entties import PortOutEntity
from .core.enums import DeviceClassControl
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

    fans = []
    for port in megad.ports:
        if isinstance(port, ReleyPortOut):
            if port.conf.device_class == DeviceClassControl.FAN:
                unique_id = f'{entry_id}-{megad.id}-{port.conf.id}'
                fans.append(FanMegaD(
                    coordinator, port, unique_id)
                )
    if fans:
        async_add_entities(fans)
        _LOGGER.debug(f'Добавлена вентиляция: {fans}')


class FanMegaD(FanEntity, PortOutEntity):

    _attr_supported_features = (FanEntityFeature.TURN_ON
                                | FanEntityFeature.TURN_OFF)

    def __init__(
            self, coordinator: MegaDCoordinator, port: ReleyPortOut,
            unique_id: str
    ) -> None:
        super().__init__(coordinator, port, unique_id)
        self.entity_id = f'fan.{self._megad.id}_port{port.conf.id}'

    def __repr__(self) -> str:
        if not self.hass:
            return f"<Fan entity {self.entity_id}>"
        return super().__repr__()

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self._port.state

    # async def async_turn_on(self, **kwargs):
    #     """Turn the entity on."""
    #     await super().async_turn_off(**kwargs)
    #     await self._switch_port(PORT_COMMAND.ON)
    #
    # async def async_turn_off(self, **kwargs):
    #     """Turn the entity off."""
    #     await super().async_turn_off(**kwargs)
    #     await self._switch_port(PORT_COMMAND.OFF)

    # async def async_toggle(self, **kwargs):
    #     """Toggle the entity."""
    #     await self._switch_port(PORT_COMMAND.TOGGLE)
