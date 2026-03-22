import asyncio
import logging
import random
from math import floor

from propcache import cached_property

from homeassistant.components.light import (
    LightEntity, ColorMode, ATTR_BRIGHTNESS, ATTR_RGB_COLOR, ATTR_EFFECT,
    LightEntityFeature
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify
from . import MegaDCoordinator
from .const import (
    DOMAIN, ENTRIES, CURRENT_ENTITY_IDS, COLOR_ORDERS, COLOR_OFF, PORT_COMMAND,
    TIME_OUT_RGB, EFFECT_OF_RGB
)
from .core.base_ports import (
    ReleyPortOut, PWMPortOut, I2CExtraPCA9685, I2CExtraMCP230xx, RGBPortOut,
    OneWirePortOut
)
from .core.entties import (
    PortOutEntity, PortOutExtraEntity, PortOutOneWireEntity
)
from .core.enums import DeviceClassControl
from .core.megad import MegaD
from .core.models_megad import (
    PCA9685RelayConfig, MCP230RelayConfig, PCA9685PWMConfig
)

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
                unique_id = f'{entry_id}-{megad.id}-{port.conf.id}-light'
                lights.append(LightPWMMegaD(
                    coordinator, port, unique_id)
                )
        if isinstance(port, RGBPortOut):
            unique_id = f'{entry_id}-{megad.id}-{port.conf.id}-light'
            lights.append(LightRGBMegaD(coordinator, port, unique_id))
        if isinstance(port, I2CExtraPCA9685):
            for config in port.extra_confs:
                if (isinstance(config, PCA9685RelayConfig) and
                        config.device_class == DeviceClassControl.LIGHT):
                    unique_id = (f'{entry_id}-{megad.id}-{port.conf.id}-'
                                 f'ext{config.id}-light')
                    lights.append(LightExtraMegaD(
                        coordinator, port, config, unique_id)
                    )
                if (isinstance(config, PCA9685PWMConfig) and
                        config.device_class == DeviceClassControl.LIGHT):
                    unique_id = (f'{entry_id}-{megad.id}-{port.conf.id}-'
                                 f'ext{config.id}-light')
                    lights.append(LightExtraPWMMegaD(
                        coordinator, port, config, unique_id)
                    )
        if isinstance(port, I2CExtraMCP230xx):
            for config in port.extra_confs:
                if (isinstance(config, MCP230RelayConfig) and
                        config.device_class == DeviceClassControl.LIGHT):
                    unique_id = (f'{entry_id}-{megad.id}-{port.conf.id}-'
                                 f'ext{config.id}-light')
                    lights.append(LightExtraMegaD(
                        coordinator, port, config, unique_id)
                    )
        if isinstance(port, OneWirePortOut):
            if (port.conf.device_class == DeviceClassControl.LIGHT):
                for id_one_wire in port.state:
                    unique_id = (f'{entry_id}-{megad.id}-{port.conf.id}-'
                                 f'{id_one_wire}-light')
                    lights.append(LightRelayMegaDOneWire(
                        coordinator, port, unique_id, id_one_wire, 'A')
                    )
                    lights.append(LightRelayMegaDOneWire(
                        coordinator, port, unique_id, id_one_wire, 'B')
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
        self.entity_id = 'light.' + slugify(
            f'{self._megad.id}_port{port.conf.id}'
        )

    def __repr__(self) -> str:
        if not self.hass:
            return f'<Light entity {self.entity_id}>'
        return super().__repr__()


class LightRelayMegaDOneWire(PortOutOneWireEntity, LightEntity):

    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_color_mode = ColorMode.ONOFF

    def __init__(
            self, coordinator: MegaDCoordinator, port: OneWirePortOut,
            unique_id: str, module_id: str, line: str
    ) -> None:
        super().__init__(coordinator, port, unique_id, module_id, line)
        self.entity_id = 'light.' + slugify(
            f'{self._megad.id}_port{port.conf.id}_{module_id.strip("0")}_{line}'
        )

    def __repr__(self) -> str:
        if not self.hass:
            return f'<Light entity {self.entity_id}>'
        return super().__repr__()


class LightPWMBaseMegaD(CoordinatorEntity, LightEntity):
    """Базовый класс для освещения с ШИМ"""

    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS

    def __init__(
            self, coordinator: MegaDCoordinator,
            min_brightness,
            max_brightness
    ) -> None:
        super().__init__(coordinator)
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self._attr_device_info = coordinator.devices_info()

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
            return floor(value + 0.5)

    def ha_to_device_brightness(self, ha_value) -> int:
        if ha_value == 0:
            return 0
        elif ha_value == 1:
            return self.min_brightness
        else:
            value = ha_value / 255 * (
                    self.max_brightness - self.min_brightness
            ) + self.min_brightness
            return floor(value + 0.5)


class LightPWMMegaD(LightPWMBaseMegaD):

    def __init__(
            self, coordinator: MegaDCoordinator, port: PWMPortOut,
            unique_id: str
    ) -> None:
        super().__init__(coordinator, port.conf.min_value, 255)
        self._coordinator: MegaDCoordinator = coordinator
        self._megad: MegaD = coordinator.megad
        self._port: PWMPortOut = port
        self._name: str = port.conf.name
        self._unique_id: str = unique_id
        self.entity_id = 'light.' + slugify(
            f'{self._megad.id}_port{port.conf.id}'
        )

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


class LightExtraMegaD(PortOutExtraEntity, LightEntity):

    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_color_mode = ColorMode.ONOFF

    def __init__(
            self, coordinator: MegaDCoordinator,
            port: I2CExtraPCA9685 | I2CExtraMCP230xx,
            config_extra_port: PCA9685RelayConfig | MCP230RelayConfig,
            unique_id: str
    ) -> None:
        super().__init__(coordinator, port, config_extra_port, unique_id)
        self.entity_id ='light.' + slugify(
            f'{self._megad.id}_port{port.conf.id}_ext{config_extra_port.id}'
        )

    def __repr__(self) -> str:
        if not self.hass:
            return f'<Light entity {self.entity_id}>'
        return super().__repr__()


class LightExtraPWMMegaD(LightPWMBaseMegaD):

    def __init__(
            self, coordinator: MegaDCoordinator,
            port: I2CExtraPCA9685,
            config_extra_port: PCA9685PWMConfig,
            unique_id: str
    ) -> None:
        super().__init__(
            coordinator,
            config_extra_port.min_value,
            config_extra_port.max_value
        )
        self._coordinator: MegaDCoordinator = coordinator
        self._megad: MegaD = coordinator.megad
        self._port: I2CExtraPCA9685 = port
        self._config_extra_port = config_extra_port
        self.ext_id = f'{port.conf.id}e{config_extra_port.id}'
        self._name: str = config_extra_port.name
        self._unique_id: str = unique_id
        self.entity_id = 'light.' + slugify(
            f'{self._megad.id}_port{port.conf.id}_ext{config_extra_port.id}'
        )

    async def set_value_port(self, value):
        """Установка значения порта"""
        try:
            await self._megad.set_port(self.ext_id, value)
            await self._coordinator.update_port_state(
                self._port.conf.id,
                {f'ext{self._config_extra_port.id}': value}
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
        return self.device_to_ha_brightness(
            self._port.state[self._config_extra_port.id]
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return bool(self.device_to_ha_brightness(
            self._port.state[self._config_extra_port.id])
        )

    async def async_turn_on(self, brightness: int = 255, **kwargs):
        """Turn the entity on."""
        if brightness is not None:
            await self.set_value_port(self.ha_to_device_brightness(brightness))

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await self.set_value_port(0)


class LightRGBMegaD(CoordinatorEntity, LightEntity):
    """Класс для RGB адресной ленты."""

    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB
    _attr_brightness = 255
    _attr_rgb_color = (255, 255, 255)
    _attr_supported_features = LightEntityFeature.EFFECT

    def __init__(
            self, coordinator: MegaDCoordinator, port: RGBPortOut,
            unique_id: str
    ) -> None:
        super().__init__(coordinator)
        self._coordinator: MegaDCoordinator = coordinator
        self._megad: MegaD = coordinator.megad
        self._port: RGBPortOut = port
        self._name: str = port.conf.name
        self._unique_id: str = unique_id
        self._color_order: str = port.conf.device_class
        self._attr_device_info = coordinator.devices_info()
        self.entity_id = 'light.' + slugify(
            f'{self._megad.id}_port{port.conf.id}'
        )
        self._effect = EFFECT_OF_RGB.NONE
        self._effect_task: asyncio.Task | None = None

    @cached_property
    def name(self) -> str:
        return self._name

    @cached_property
    def unique_id(self) -> str:
        return self._unique_id

    def __repr__(self) -> str:
        if not self.hass:
            return f"<Light entity {self.entity_id}>"
        return super().__repr__()

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self._port.state

    def _get_color_order(self) -> tuple[int, int, int]:
        """Get color order mapping based on configuration."""
        if self._color_order not in COLOR_ORDERS:
            _LOGGER.warning(
                f'Unknown color order {self._color_order}, falling back to RGB'
            )
            return COLOR_ORDERS['rgb']
        return COLOR_ORDERS[self._color_order]

    def _convert_color(self,
                       rgb: tuple[int, int, int],
                       brightness: int) -> str:
        """Конвертирует в формат для MegaD."""
        factor = brightness / 255.0
        scaled = [int(c * factor) for c in rgb]

        r_idx, g_idx, b_idx = self._get_color_order()
        true_order = (scaled[r_idx], scaled[g_idx], scaled[b_idx])
        conver_value = (f'{true_order[0]:02x}'
                        f'{true_order[1]:02x}'
                        f'{true_order[2]:02x}').upper()
        _LOGGER.debug(f'{rgb} was converted to {conver_value}')
        return conver_value

    async def _set_color(self, rgb):
        color_hex = self._convert_color(rgb, self._attr_brightness)
        await self._megad.set_color_port(self._port.conf.id, color_hex)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the light on."""
        _LOGGER.debug(f'Turn on with {kwargs}')
        rgb = self._attr_rgb_color
        if ATTR_EFFECT in kwargs:
            self._effect = kwargs[ATTR_EFFECT]
            await self._start_effect()
            rgb = (255, 255, 255)
        if ATTR_BRIGHTNESS in kwargs:
            self._attr_brightness = kwargs[ATTR_BRIGHTNESS]
        if ATTR_RGB_COLOR in kwargs:
            rgb = kwargs[ATTR_RGB_COLOR]
        if self._port.conf.port_out is not None:
            port_out = self._megad.get_port(self._port.conf.port_out)
            if not port_out.state:
                await self._megad.set_port(port_out.conf.id, PORT_COMMAND.ON)
                port_out.update_state(PORT_COMMAND.ON)
                await self._coordinator.update_port_state(
                    port_out.conf.id, PORT_COMMAND.ON
                )
                await asyncio.sleep(TIME_OUT_RGB)
        if not ATTR_EFFECT in kwargs:
            await self._set_color(rgb)
        self._attr_rgb_color = rgb
        self._port.update_state(True)
        await self._coordinator.update_port_state(
            self._port.conf.id, True
        )
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the light off."""
        await self._stop_effect()
        self._effect = EFFECT_OF_RGB.NONE
        await self._megad.set_color_port(self._port.conf.id, COLOR_OFF)
        await self._coordinator.update_port_state(
            self._port.conf.id, False
        )
        if self._port.conf.port_out is not None:
            port_out = self._megad.get_port(self._port.conf.port_out)
            await self._megad.set_port(port_out.conf.id, PORT_COMMAND.OFF)
            port_out.update_state(PORT_COMMAND.OFF)
            await self._coordinator.update_port_state(
                port_out.conf.id, PORT_COMMAND.OFF
            )

    @property
    def effect_list(self) -> list[str]:
        return [EFFECT_OF_RGB.NONE, EFFECT_OF_RGB.ALARM, EFFECT_OF_RGB.GARLAND]

    @property
    def effect(self) -> str | None:
        return self._effect

    async def _start_effect(self):
        await self._stop_effect()

        if self._effect == EFFECT_OF_RGB.NONE:
            return

        if self._effect == EFFECT_OF_RGB.ALARM:
            self._effect_task = asyncio.create_task(self._effect_alarm())

        elif self._effect == EFFECT_OF_RGB.GARLAND:
            self._effect_task = asyncio.create_task(self._effect_garland())

    async def _stop_effect(self):
        if self._effect_task:
            self._effect_task.cancel()
            try:
                await self._effect_task
            except asyncio.CancelledError:
                pass
            self._effect_task = None

    async def _effect_alarm(self):
        try:
            while True:
                await self._set_color((255, 0, 0))
                await asyncio.sleep(1.5)

                await self._set_color((0, 0, 255))
                await asyncio.sleep(1.5)

        except asyncio.CancelledError:
            pass

    @staticmethod
    def _random_bright_color():
        return random.choice([
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (255, 255, 0),
            (0, 255, 255),
            (255, 0, 255),
            (255, 255, 255),
        ])

    def _random_strip_bright(self, chips: int) -> str:
        result = []
        if chips > 133:
            chips = 133
        for _ in range(chips):
            r, g, b = self._random_bright_color()
            result.append(f'{r:02X}{g:02X}{b:02X}')

        return ''.join(result)

    async def _effect_garland(self):
        try:
            count_chip = self._port.conf.chip

            while True:
                color = self._random_strip_bright(count_chip)
                await self._megad.set_color_port(self._port.conf.id, color)
                await asyncio.sleep(5)

        except asyncio.CancelledError:
            pass
