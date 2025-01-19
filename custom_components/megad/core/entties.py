import logging

from propcache import cached_property

from config.custom_components.megad import MegaDCoordinator
from config.custom_components.megad.const import PORT_COMMAND
from config.custom_components.megad.core.base_ports import ReleyPortOut
from config.custom_components.megad.core.megad import MegaD
from homeassistant.helpers.update_coordinator import CoordinatorEntity


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
            await self._megad.set_port(self._port.conf.id, command)
            if command == PORT_COMMAND.TOGGLE:
                if self._port.state:
                    await self._coordinator.update_port_state(
                        self._port.conf.id, PORT_COMMAND.OFF
                    )
                else:
                    await self._coordinator.update_port_state(
                        self._port.conf.id, PORT_COMMAND.ON
                    )
            else:
                await self._megad.set_port(self._port.conf.id, command)
                await self._coordinator.update_port_state(
                    self._port.conf.id, command
                )
        except Exception as e:
            _LOGGER.warning(f'Ошибка управления портом '
                            f'{self._port.conf.id}: {e}')

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        await self._switch_port(PORT_COMMAND.ON)

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await self._switch_port(PORT_COMMAND.OFF)

    async def async_toggle(self, **kwargs):
        """Toggle the entity."""
        await self._switch_port(PORT_COMMAND.TOGGLE)
