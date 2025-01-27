import logging
from typing import Optional, Any

from propcache import cached_property

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from . import MegaDCoordinator
from .const import DOMAIN, PORT_COMMAND, ENTRIES, CURRENT_ENTITY_IDS
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
    coordinator = hass.data[DOMAIN][ENTRIES][entry_id]
    megad = coordinator.megad

    fans = []
    for port in megad.ports:
        if isinstance(port, ReleyPortOut):
            if port.conf.device_class == DeviceClassControl.FAN:
                unique_id = f'{entry_id}-{megad.id}-{port.conf.id}'
                fans.append(FanMegaD(
                    coordinator, port, unique_id)
                )
        if isinstance(port, PWMPortOut):
            if port.conf.device_class == DeviceClassControl.FAN:
                unique_id = f'{entry_id}-{megad.id}-{port.conf.id}'
                fans.append(FanWMMegaD(
                    coordinator, port, unique_id)
                )
    for fan in fans:
        hass.data[DOMAIN][CURRENT_ENTITY_IDS][entry_id].append(
            fan.unique_id)
    if fans:
        async_add_entities(fans)
        _LOGGER.debug(f'Добавлена вентиляция: {fans}')


class FanMegaD(PortOutEntity, FanEntity):

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

    async def async_turn_on(
            self, speed: Optional[str] = None,
            percentage: Optional[int] = None,
            preset_mode: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Turn the entity on."""
        await self._switch_port(PORT_COMMAND.ON)

    async def async_turn_off(
            self, speed: Optional[str] = None,
            percentage: Optional[int] = None,
            preset_mode: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Turn the entity off."""
        await super().async_turn_off(**kwargs)
        await self._switch_port(PORT_COMMAND.OFF)

    async def async_toggle(
            self, speed: Optional[str] = None,
            percentage: Optional[int] = None,
            preset_mode: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Toggle the entity."""
        await self._switch_port(PORT_COMMAND.TOGGLE)


class FanWMMegaD(CoordinatorEntity, FanEntity):

    _attr_supported_features = (FanEntityFeature.TURN_ON
                                | FanEntityFeature.TURN_OFF
                                | FanEntityFeature.SET_SPEED)

    def __init__(
            self, coordinator: MegaDCoordinator, port: PWMPortOut,
            unique_id: str
    ) -> None:
        super().__init__(coordinator)
        self._coordinator: MegaDCoordinator = coordinator
        self._megad: MegaD = coordinator.megad
        self._port: PWMPortOut = port
        self._name: str = port.conf.name
        self._unique_id: str = unique_id
        self.min_speed = port.conf.min_value
        self.max_speed = 255
        self._attr_device_info = coordinator.devices_info()
        self.entity_id = f'fan.{self._megad.id}_port{port.conf.id}'

    def __repr__(self) -> str:
        if not self.hass:
            return f"<Fan entity {self.entity_id}>"
        return super().__repr__()

    def device_to_ha_speed(self, device_value) -> int:
        if device_value < self.min_speed or device_value == 0:
            return 0
        elif device_value == self.min_speed:
            return 1
        else:
            value = (device_value - self.min_speed) / (
                (self.max_speed - self.min_speed)) * 100
            return int(value)

    def ha_to_device_speed(self, ha_value) -> int:
        if ha_value == 0:
            return 0
        elif ha_value == 1:
            return self.min_speed
        else:
            value = ha_value / 100 * (
                    self.max_speed - self.min_speed) + self.min_speed
            return int(value)

    async def set_value_port(self, value):
        """Установка значения порта"""
        try:
            await self._megad.set_port(self._port.conf.id, value)
            await self._coordinator.update_port_state(
                self._port.conf.id, value
            )
        except Exception as e:
            _LOGGER.warning(f'Ошибка управления портом '
                            f'{self._port.conf.id}: {e}')

    @cached_property
    def name(self) -> str:
        return self._name

    @cached_property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def percentage(self) -> int | None:
        """Return the current speed as a percentage."""
        return self.device_to_ha_speed(self._port.state)

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed of the fan, as a percentage."""
        if percentage == 0:
            await self.async_turn_off()
        await self.set_value_port(self.ha_to_device_speed(percentage))

    async def async_turn_on(
            self, speed: Optional[str] = None,
            percentage: Optional[int] = None,
            preset_mode: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Turn the entity on."""
        await self.set_value_port(self.ha_to_device_speed(100))

    async def async_turn_off(
            self, speed: Optional[str] = None,
            percentage: Optional[int] = None,
            preset_mode: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Turn the entity off."""
        await self.set_value_port(0)
