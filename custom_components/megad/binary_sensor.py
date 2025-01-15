import logging

from propcache import cached_property

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass, BinarySensorEntity
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from . import MegaDCoordinator

from .const import DOMAIN
from .core.base_ports import BinaryPortIn
from .core.enums import DeviceClassBinary
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

    binary_sensors = []
    for port in megad.ports:
        if isinstance(port, BinaryPortIn):
            unique_id = f'{entry_id}-{megad.id}-{port.conf.id}'
            binary_sensors.append(BinarySensorMegaD(
                coordinator, port, unique_id)
            )
    if binary_sensors:
        async_add_entities(binary_sensors)
        _LOGGER.debug(f'Добавлены бинарные сенсоры: {binary_sensors}')


class BinarySensorMegaD(CoordinatorEntity, BinarySensorEntity):

    def __init__(
            self, coordinator: MegaDCoordinator, port: BinaryPortIn,
            unique_id: str
    ) -> None:
        super().__init__(coordinator)
        self._megad: MegaD = coordinator.megad
        self._port: BinaryPortIn = port
        self._binary_sensor_name: str = port.conf.name
        self._unique_id: str = unique_id
        self._attr_device_info = coordinator.devices_info()
        self.entity_id = f'binary_sensor.{self._megad.id}_port{port.conf.id}'

    def __repr__(self) -> str:
        if not self.hass:
            return f"<Binary sensor entity {self.entity_id}>"
        return super().__repr__()

    @cached_property
    def name(self) -> str:
        if 'port' in self._binary_sensor_name:
            return f'{self._megad.id}_{self._binary_sensor_name}'
        return self._binary_sensor_name

    @cached_property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self._port.state

    @cached_property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return the class of this entity."""

        match self._port.conf.device_class.value:
            case DeviceClassBinary.SMOKE.value:
                return BinarySensorDeviceClass.SMOKE
            case DeviceClassBinary.DOOR.value:
                return BinarySensorDeviceClass.DOOR
            case DeviceClassBinary.MOTION.value:
                return BinarySensorDeviceClass.MOTION
            case DeviceClassBinary.GARAGE_DOOR.value:
                return BinarySensorDeviceClass.GARAGE_DOOR
            case DeviceClassBinary.LOCK.value:
                return BinarySensorDeviceClass.LOCK
            case DeviceClassBinary.MOISTURE.value:
                return BinarySensorDeviceClass.MOISTURE
            case DeviceClassBinary.WINDOW.value:
                return BinarySensorDeviceClass.WINDOW
            case _:
                return None

    # @callback
    # def _handle_coordinator_update(self) -> None:
    #     """Обработка обновлённых данных от координатора"""
    #
    #     _LOGGER.info(self.coordinator)
    #     # port: BinaryPortIn = self.coordinator.
    #     # self._sensor = sensor
    #     self.async_write_ha_state()
