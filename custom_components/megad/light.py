import logging

from propcache import cached_property

from homeassistant.components.light import LightEntity, ColorMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from . import MegaDCoordinator
from .const import DOMAIN, ENTRIES, CURRENT_ENTITY_IDS
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

    lights = []
    for port in megad.ports:
        if isinstance(port, ReleyPortOut):
            if port.conf.device_class == DeviceClassControl.LIGHT:
                unique_id = f'{entry_id}-{megad.id}-{port.conf.id}-light'
                lights.append(LightRelayMegaD(
                    coordinator, port, unique_id)
                )
        if isinstance(port, PWMPortOut):
            if port.conf.device_class == DeviceClassControl.LIGHT:
                unique_id = f'{entry_id}-{megad.id}-{port.conf.id}--light'
                lights.append(LightPWMMegaD(
                    coordinator, port, unique_id)
                )
    for light in lights:
        hass.data[DOMAIN][CURRENT_ENTITY_IDS][entry_id].append(
            light.unique_id)
    if lights:
        async_add_entities(lights)
        _LOGGER.debug(f'Добавлено освещение: {lights}')


class LightRelayMegaD(PortOutEntity, LightEntity):

    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_color_mode = ColorMode.ONOFF

    def __init__(
            self, coordinator: MegaDCoordinator, port: ReleyPortOut,
            unique_id: str
    ) -> None:
        super().__init__(coordinator, port, unique_id)
        self.entity_id = f'light.{self._megad.id}_port{port.conf.id}'

    def __repr__(self) -> str:
        if not self.hass:
            return f"<Light entity {self.entity_id}>"
        return super().__repr__()


class LightPWMMegaD(CoordinatorEntity, LightEntity):

    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS

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
        self.min_brightness = port.conf.min_value
        self.max_brightness = 255
        self._attr_device_info = coordinator.devices_info()
        self.entity_id = f'light.{self._megad.id}_port{port.conf.id}'

    def __repr__(self) -> str:
        if not self.hass:
            return f"<Light entity {self.entity_id}>"
        return super().__repr__()

    def device_to_ha_brightness(self, device_value) -> int:
        if device_value < self.min_brightness or device_value == 0:
            return 0
        elif device_value == self.min_brightness:
            return 1
        else:
            value = (device_value - self.min_brightness) / (
                (self.max_brightness - self.min_brightness)) * 255
            return int(value)

    def ha_to_device_brightness(self, ha_value) -> int:
        if ha_value == 0:
            return 0
        elif ha_value == 1:
            return self.min_brightness
        else:
            value = ha_value / self.max_brightness * (
                    self.max_brightness - self.min_brightness
            ) + self.min_brightness
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
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0..255."""
        return self.device_to_ha_brightness(self._port.state)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return bool(self.device_to_ha_brightness(self._port.state))

    async def async_turn_on(self, brightness: int = 255, **kwargs):
        """Turn the entity on."""
        if brightness is not None:
            await self.set_value_port(self.ha_to_device_brightness(brightness))

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await self.set_value_port(0)
