import logging

from propcache import cached_property

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from . import MegaDCoordinator
from .const import DOMAIN, PORT_COMMAND, ENTRIES, CURRENT_ENTITY_IDS
from .core.base_ports import (
    ReleyPortOut, PWMPortOut, I2CExtraPCA9685, I2CExtraMCP230xx
)
from .core.entties import PortOutEntity, PortOutExtraEntity
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
    groups = {}

    switches = []
    for port in megad.ports:
        if isinstance(port, ReleyPortOut):
            if port.conf.device_class == DeviceClassControl.SWITCH:
                unique_id = f'{entry_id}-{megad.id}-{port.conf.id}-switch'
                switches.append(SwitchMegaD(
                    coordinator, port, unique_id)
                )
        if isinstance(port, (ReleyPortOut, PWMPortOut)):
            if port.conf.group is not None:
                groups.setdefault(port.conf.group, []).append(port.conf.id)
        if isinstance(port, I2CExtraPCA9685):
            for config in port.extra_confs:
                if (isinstance(config, PCA9685RelayConfig) and
                        config.device_class == DeviceClassControl.SWITCH):
                    unique_id = (f'{entry_id}-{megad.id}-{port.conf.id}-'
                                 f'ext{config.id}-switch')
                    switches.append(SwitchExtraMegaD(
                        coordinator, port, config, unique_id)
                    )
                if config.group is not None:
                    groups.setdefault(config.group, []).append(
                        f'{port.conf.id}e{config.id}'
                    )
        if isinstance(port, I2CExtraMCP230xx):
            for config in port.extra_confs:
                if (isinstance(config, MCP230RelayConfig) and
                        config.device_class == DeviceClassControl.SWITCH):
                    unique_id = (f'{entry_id}-{megad.id}-{port.conf.id}-'
                                 f'ext{config.id}-switch')
                    switches.append(SwitchExtraMegaD(
                        coordinator, port, config, unique_id)
                    )
    if groups:
        for group, ports in groups.items():
            unique_id = f'{entry_id}-{megad.id}-group{group}'
            name = f'{megad.id}_group{group}'
            switches.append(SwitchGroupMegaD(
                coordinator, group, name, ports, unique_id)
            )
    for switch in switches:
        hass.data[DOMAIN][CURRENT_ENTITY_IDS][entry_id].append(
            switch.unique_id)
    if switches:
        async_add_entities(switches)
        _LOGGER.debug(f'Добавлены переключатели: {switches}')


class SwitchMegaD(PortOutEntity, SwitchEntity):

    def __init__(
            self, coordinator: MegaDCoordinator, port: ReleyPortOut,
            unique_id: str
    ) -> None:
        super().__init__(coordinator, port, unique_id)
        self.entity_id = f'switch.{self._megad.id}_port{port.conf.id}'

    def __repr__(self) -> str:
        if not self.hass:
            return f"<Switch entity {self.entity_id}>"
        return super().__repr__()


class SwitchGroupMegaD(CoordinatorEntity, SwitchEntity):

    def __init__(
            self, coordinator: MegaDCoordinator, group: int, name: str,
            ports: list, unique_id: str
    ) -> None:
        super().__init__(coordinator)
        self._coordinator: MegaDCoordinator = coordinator
        self._megad: MegaD = coordinator.megad
        self._ports: list = ports
        self._group: int = group
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

    @staticmethod
    def _check_command(port, command: PORT_COMMAND, ext_id=None) -> str:
        """
        Проверка порта на возможность диммирования и корректировка команды.
        """
        if ext_id is not None:
            conf_ext = port.extra_confs[ext_id]
            if isinstance(conf_ext, PCA9685PWMConfig):
                max_value = conf_ext.max_value
                return max_value if command == PORT_COMMAND.ON else command
        if isinstance(port, PWMPortOut):
            return '255' if command == PORT_COMMAND.ON else command
        else:
            return command

    async def _switch_group(self, command):
        """Переключение состояния группы выходов"""
        port_states = {}
        try:
            await self._megad.set_port(f'g{self._group}', command)
            if command == PORT_COMMAND.TOGGLE:
                for port_id in self._ports:
                    ext_id = None
                    if isinstance(port_id, str):
                        port_id, ext_id = port_id.split('e')
                        port_id = int(port_id)
                        ext_id = int(ext_id)
                    port = self._megad.get_port(port_id)
                    if ext_id is not None:
                        if port.state[ext_id]:
                            port_states.setdefault(port_id, {})[
                                f'ext{ext_id}'] = (
                                PORT_COMMAND.ON
                                if port.conf.inverse else
                                PORT_COMMAND.OFF
                            )
                        else:
                            port_states.setdefault(port_id, {})[
                                f'ext{ext_id}'] = (
                                PORT_COMMAND.OFF
                                if port.conf.inverse else
                                self._check_command(
                                    port, PORT_COMMAND.ON, ext_id
                                )
                            )
                    else:
                        if port.state:
                            port_states[port_id] = (
                                PORT_COMMAND.ON
                                if port.conf.inverse else
                                PORT_COMMAND.OFF
                            )
                        else:
                            port_states[port_id] = (
                                PORT_COMMAND.OFF
                                if port.conf.inverse else
                                self._check_command(port, PORT_COMMAND.ON)
                            )
            else:
                for port_id in self._ports:
                    if isinstance(port_id, str):
                        port_id, ext_id = port_id.split('e')
                        port_id = int(port_id)
                        ext_id = int(ext_id)
                        port = self._megad.get_port(port_id)
                        port_states.setdefault(port_id, {})[
                            f'ext{ext_id}'] = self._check_command(
                            port, command, ext_id
                        )
                    else:
                        port_states[port_id] = self._check_command(
                            self._megad.get_port(port_id), command
                        )
            self._coordinator.update_group_state(port_states)
        except Exception as e:
            _LOGGER.warning(f'Ошибка управления группой портов '
                            f'{self._group}: {e}')

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        await self._switch_group(PORT_COMMAND.ON)

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await self._switch_group(PORT_COMMAND.OFF)

    async def async_toggle(self, **kwargs):
        """Toggle the entity."""
        await self._switch_group(PORT_COMMAND.TOGGLE)


class SwitchExtraMegaD(PortOutExtraEntity, SwitchEntity):

    def __init__(
            self, coordinator: MegaDCoordinator,
            port: I2CExtraPCA9685 | I2CExtraMCP230xx,
            config_extra_port: PCA9685RelayConfig | MCP230RelayConfig,
            unique_id: str
    ) -> None:
        super().__init__(coordinator, port, config_extra_port, unique_id)
        self.entity_id = (f'switch.{self._megad.id}_port{port.conf.id}_'
                          f'ext{config_extra_port.id}')

    def __repr__(self) -> str:
        if not self.hass:
            return f"<Switch entity {self.entity_id}>"
        return super().__repr__()
