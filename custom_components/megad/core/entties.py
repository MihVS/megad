import logging

from propcache import cached_property

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .base_ports import ReleyPortOut
from .megad import MegaD
from .. import MegaDCoordinator
from ..const import PORT_COMMAND

_LOGGER = logging.getLogger(__name__)


class PortOutEntity(CoordinatorEntity):

    def __init__(
            self, coordinator: MegaDCoordinator, port: ReleyPortOut,
            unique_id: str
    ) -> None:
        super().__init__(coordinator)
        self._coordinator: MegaDCoordinator = coordinator
        self._megad: MegaD = coordinator.megad
        self._port: ReleyPortOut = port
        self._name: str = port.conf.name
        self._unique_id: str = unique_id
        self._attr_device_info = coordinator.devices_info()

    @cached_property
    def name(self) -> str:
        return self._name

    @cached_property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self._port.state

    async def _switch_port(self, command):
        """Переключение состояния порта"""
        try:
            await self._megad.set_port(
                self._port.conf.id, self._check_inverse(command)
            )
            if command == PORT_COMMAND.TOGGLE:
                if self._port.state:
                    await self._coordinator.update_port_state(
                        self._port.conf.id,
                        self._check_inverse(PORT_COMMAND.OFF)
                    )
                else:
                    await self._coordinator.update_port_state(
                        self._port.conf.id,
                        self._check_inverse(PORT_COMMAND.ON)
                    )
            else:
                await self._coordinator.update_port_state(
                    self._port.conf.id, self._check_inverse(command)
                )
        except Exception as e:
            _LOGGER.warning(f'Ошибка управления портом '
                            f'{self._port.conf.id}: {e}')

    def _check_inverse(self, command) -> PORT_COMMAND:
        """Проверяет необходимость инверсии и возвращает правильную команду"""
        if command == PORT_COMMAND.ON:
            return (
                PORT_COMMAND.OFF
                if self._port.conf.inverse else
                PORT_COMMAND.ON
            )
        elif command == PORT_COMMAND.OFF:
            return (
                PORT_COMMAND.ON
                if self._port.conf.inverse else
                PORT_COMMAND.OFF
            )
        else:
            return command

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        await self._switch_port(PORT_COMMAND.ON)

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await self._switch_port(PORT_COMMAND.OFF)

    async def async_toggle(self, **kwargs):
        """Toggle the entity."""
        await self._switch_port(PORT_COMMAND.TOGGLE)


class PortOutExtraEntity(CoordinatorEntity):

    def __init__(
            self, coordinator: MegaDCoordinator, port,
            config_extra_port, unique_id: str
    ) -> None:
        super().__init__(coordinator)
        self._coordinator: MegaDCoordinator = coordinator
        self._megad: MegaD = coordinator.megad
        self._config_extra_port = config_extra_port
        self._port = port
        self.ext_id = f'{self._port.conf.id}e{self._config_extra_port.id}'
        self._name: str = config_extra_port.name
        self._unique_id: str = unique_id
        self._attr_device_info = coordinator.devices_info()

    @cached_property
    def name(self) -> str:
        return self._name

    @cached_property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if self._port.state:
            return bool(self._port.state[self._config_extra_port.id])

    async def _switch_port(self, command):
        """Переключение состояния порта"""
        try:
            await self._megad.set_port(
                self.ext_id, self._check_inverse(command)
            )
            if command == PORT_COMMAND.TOGGLE:
                if self._port.state[self._config_extra_port.id]:
                    await self._coordinator.update_port_state(
                        self._port.conf.id,
                        {f'ext{self._config_extra_port.id}':
                             self._check_inverse(PORT_COMMAND.OFF)}
                    )
                else:
                    await self._coordinator.update_port_state(
                        self._port.conf.id,
                        {f'ext{self._config_extra_port.id}':
                             self._check_inverse(PORT_COMMAND.ON)}
                    )
            else:
                await self._coordinator.update_port_state(
                    self._port.conf.id,
                    {f'ext{self._config_extra_port.id}':
                         self._check_inverse(command)}
                )
        except Exception as e:
            _LOGGER.warning(f'Ошибка управления портом '
                            f'{self._port.conf.id}: {e}')

    def _check_inverse(self, command) -> PORT_COMMAND:
        """Проверяет необходимость инверсии и возвращает правильную команду"""
        if command == PORT_COMMAND.ON:
            return (
                PORT_COMMAND.OFF
                if self._config_extra_port.inverse else
                PORT_COMMAND.ON
            )
        elif command == PORT_COMMAND.OFF:
            return (
                PORT_COMMAND.ON
                if self._config_extra_port.inverse else
                PORT_COMMAND.OFF
            )
        else:
            return command

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        await self._switch_port(PORT_COMMAND.ON)

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await self._switch_port(PORT_COMMAND.OFF)

    async def async_toggle(self, **kwargs):
        """Toggle the entity."""
        await self._switch_port(PORT_COMMAND.TOGGLE)
