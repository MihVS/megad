import logging

import async_timeout
from propcache import cached_property

from homeassistant.components.binary_sensor import (
    BinarySensorEntity
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from . import MegaDCoordinator
from .const import DOMAIN, PORT_COMMAND, TIME_OUT_UPDATE_DATA
from .core.base_ports import ReleyPortOut, PWMPortOut
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
    groups = {}

    switches = []
    for port in megad.ports:
        if isinstance(port, ReleyPortOut):
            if port.conf.device_class == DeviceClassControl.SWITCH:
                unique_id = f'{entry_id}-{megad.id}-{port.conf.id}'
                switches.append(SwitchMegaD(
                    coordinator, port, unique_id)
                )
        if isinstance(port, (ReleyPortOut, PWMPortOut)):
            if port.conf.group is not None:
                groups.setdefault(port.conf.group, []).append(port.conf.id)
    if groups:
        for group, ports in groups.items():
            unique_id = f'{entry_id}-{megad.id}-group{group}'
            name = f'{megad.id}_group{group}'
            switches.append(SwitchGroupMegaD(
                coordinator, group, name, ports, unique_id)
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
        try:
            async with async_timeout.timeout(TIME_OUT_UPDATE_DATA):
                await self._megad.set_port(
                    self._port.conf.id, PORT_COMMAND.ON
                )
            self._port.update_state('on')
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.warning(f'Ошибка управления портом '
                            f'{self._port.conf.id}: {e}')

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        try:
            async with async_timeout.timeout(TIME_OUT_UPDATE_DATA):
                await self._megad.set_port(
                    self._port.conf.id, PORT_COMMAND.OFF
                )
            self._port.update_state('off')
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.warning(f'Ошибка управления портом '
                            f'{self._port.conf.id}: {e}')

    async def async_toggle(self, **kwargs):
        """Toggle the entity."""
        try:
            async with async_timeout.timeout(TIME_OUT_UPDATE_DATA):
                await self._megad.set_port(
                    self._port.conf.id, PORT_COMMAND.TOGGLE
                )
            if self._port.state:
                self._port.update_state('off')
            else:
                self._port.update_state('on')
            self.async_write_ha_state()

        except Exception as e:
            _LOGGER.warning(f'Ошибка управления портом '
                            f'{self._port.conf.id}: {e}')


class SwitchGroupMegaD(CoordinatorEntity, BinarySensorEntity):

    def __init__(
            self, coordinator: MegaDCoordinator, group: int, name: str,
            ports: list, unique_id: str
    ) -> None:
        super().__init__(coordinator)
        self._megad: MegaD = coordinator.megad
        self._ports: list = ports
        self._switch_name: str = name
        self._unique_id: str = unique_id
        self._attr_device_info = coordinator.devices_info()

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
        pass

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        # try:
        #     async with async_timeout.timeout(TIME_OUT_UPDATE_DATA):
        #         await self._megad.set_port(
        #             self._port.conf.id, PORT_COMMAND.ON
        #         )
        #     self._port.update_state('on')
        #     self.async_write_ha_state()
        # except Exception as e:
        #     _LOGGER.warning(f'Ошибка управления портом '
        #                     f'{self._port.conf.id}: {e}')

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        # try:
        #     async with async_timeout.timeout(TIME_OUT_UPDATE_DATA):
        #         await self._megad.set_port(
        #             self._port.conf.id, PORT_COMMAND.OFF
        #         )
        #     self._port.update_state('off')
        #     self.async_write_ha_state()
        # except Exception as e:
        #     _LOGGER.warning(f'Ошибка управления портом '
        #                     f'{self._port.conf.id}: {e}')

    async def async_toggle(self, **kwargs):
        """Toggle the entity."""
        # try:
        #     async with async_timeout.timeout(TIME_OUT_UPDATE_DATA):
        #         await self._megad.set_port(
        #             self._port.conf.id, PORT_COMMAND.TOGGLE
        #         )
        #     if self._port.state:
        #         self._port.update_state('off')
        #     else:
        #         self._port.update_state('on')
        #     self.async_write_ha_state()
        #
        # except Exception as e:
        #     _LOGGER.warning(f'Ошибка управления портом '
        #                     f'{self._port.conf.id}: {e}')
