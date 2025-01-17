import logging

from propcache import cached_property

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from . import MegaDCoordinator
from .const import DOMAIN, STATE_BUTTON
from .core.base_ports import (
    BinaryPortClick, BinaryPortCount, BinaryPortIn
)
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

    sensors = []
    for port in megad.ports:
        if isinstance(port, BinaryPortClick):
            unique_id = f'{entry_id}-{megad.id}-{port.conf.id}'
            sensors.append(ClickSensorMegaD(
                coordinator, port, unique_id)
            )
        if isinstance(port, (BinaryPortCount, BinaryPortClick, BinaryPortIn)):
            unique_id = f'{entry_id}-{megad.id}-{port.conf.id}-count'
            sensors.append(CountSensorMegaD(
                coordinator, port, unique_id)
            )
    if sensors:
        async_add_entities(sensors)
        _LOGGER.debug(f'Добавлены сенсоры: {sensors}')


class ClickSensorMegaD(CoordinatorEntity, SensorEntity):

    _attr_icon = 'mdi:gesture-tap-button'

    def __init__(
            self, coordinator: MegaDCoordinator, port: BinaryPortClick,
            unique_id: str
    ) -> None:
        super().__init__(coordinator)
        self._megad: MegaD = coordinator.megad
        self._port: BinaryPortClick = port
        self._sensor_name: str = port.conf.name
        self._unique_id: str = unique_id
        self._attr_device_info = coordinator.devices_info()
        self.entity_id = f'sensor.{self._megad.id}_port{port.conf.id}'

    def __repr__(self) -> str:
        if not self.hass:
            return f"<Sensor entity {self.entity_id}>"
        return super().__repr__()

    @cached_property
    def name(self) -> str:
        return self._sensor_name

    @cached_property
    def unique_id(self) -> str:
        return self._unique_id

    @cached_property
    def capability_attributes(self):
        return {
            "options": STATE_BUTTON
        }

    @property
    def native_value(self) -> str:
        """Возвращает состояние сенсора"""
        return self._port.state


class CountSensorMegaD(CoordinatorEntity, SensorEntity):

    _attr_icon = 'mdi:counter'

    def __init__(
            self, coordinator: MegaDCoordinator, port: BinaryPortClick,
            unique_id: str
    ) -> None:
        super().__init__(coordinator)
        self._megad: MegaD = coordinator.megad
        self._port: (BinaryPortClick, BinaryPortIn, BinaryPortCount) = port
        self._unique_id: str = unique_id
        self._attr_device_info = coordinator.devices_info()

    def __repr__(self) -> str:
        if not self.hass:
            return f"<Sensor entity {self.entity_id}>"
        return super().__repr__()

    @cached_property
    def state_class(self) -> SensorStateClass | str | None:
        """Return the state class of this entity, if any."""
        return SensorStateClass.TOTAL_INCREASING

    @cached_property
    def name(self) -> str:
        return f'{self._megad.id}_port{self._port.conf.id}_count'

    @cached_property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def native_value(self) -> str:
        """Возвращает состояние сенсора"""
        return self._port.count
