import logging

from propcache import cached_property

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from . import MegaDCoordinator
from .const import (
    DOMAIN, STATE_BUTTON, SENSOR_UNIT, SENSOR_CLASS, TEMPERATURE, UPTIME,
    HUMIDITY, ENTRIES, CURRENT_ENTITY_IDS, CO2, TYPE_SENSOR_RUS, PRESSURE,
    TYPE_SENSOR, TEMPERATURE_CONDITION, DEVIATION_TEMPERATURE,
    ALLOWED_TEMP_JUMP, ALLOWED_HUM_JUMP, CURRENT, VOLTAGE, RAW_VALUE, LUXURY
)
from .core.base_pids import PIDControl
from .core.base_ports import (
    BinaryPortClick, BinaryPortCount, BinaryPortIn, OneWireSensorPort,
    DigitalSensorBase, DHTSensorPort, OneWireBusSensorPort, I2CSensorSCD4x,
    I2CSensorSTH31, AnalogSensor, I2CSensorHTUxxD, I2CSensorMBx280, ReaderPort,
    I2CSensorINA226, I2CSensorBH1750, I2CSensorT67xx, I2CSensorBMP180
)
from .core.megad import MegaD

_LOGGER = logging.getLogger(__name__)


def create_temp_hum(sensors, entry_id, coordinator, megad, port):
    """Создаём сенсоры температуры и влажности."""
    prefix = port.prefix
    unique_id_temp = (f'{entry_id}-{megad.id}-{port.conf.id}-'
                      f'{TEMPERATURE}{prefix}')
    sensors.append(SensorMegaD(
        coordinator, port, unique_id_temp, TEMPERATURE, prefix)
    )
    unique_id_hum = f'{entry_id}-{megad.id}-{port.conf.id}-{HUMIDITY}{prefix}'
    sensors.append(SensorMegaD(
        coordinator, port, unique_id_hum, HUMIDITY, prefix)
    )


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback
) -> None:
    entry_id = config_entry.entry_id
    coordinator = hass.data[DOMAIN][ENTRIES][entry_id]
    megad = coordinator.megad

    sensors = []
    for port in megad.ports:
        if isinstance(port, BinaryPortClick):
            unique_id = f'{entry_id}-{megad.id}-{port.conf.id}-click'
            sensors.append(ClickSensorMegaD(
                coordinator, port, unique_id)
            )
        if isinstance(port, (BinaryPortCount, BinaryPortClick, BinaryPortIn)):
            unique_id = f'{entry_id}-{megad.id}-{port.conf.id}-count'
            sensors.append(CountSensorMegaD(
                coordinator, port, unique_id)
            )
        if isinstance(port, ReaderPort):
            unique_id = f'{entry_id}-{megad.id}-{port.conf.id}-reader'
            sensors.append(ReaderSensorMegaD(
                coordinator, port, unique_id)
            )
        if isinstance(port, OneWireSensorPort):
            unique_id = f'{entry_id}-{megad.id}-{port.conf.id}-1wire'
            sensors.append(SensorMegaD(
                coordinator, port, unique_id, TEMPERATURE)
            )
        if isinstance(port, (DHTSensorPort, I2CSensorSTH31, I2CSensorHTUxxD)):
            create_temp_hum(sensors, entry_id, coordinator, megad, port)
        if isinstance(port, OneWireBusSensorPort):
            for id_one_wire in port.state:
                unique_id = (f'{entry_id}-{megad.id}-{port.conf.id}-'
                             f'{id_one_wire}')
                sensors.append(SensorBusMegaD(
                    coordinator, port, unique_id, TEMPERATURE, id_one_wire)
                )
        if isinstance(port, I2CSensorSCD4x):
            prefix = port.prefix
            unique_id_co2 = (f'{entry_id}-{megad.id}-{port.conf.id}-'
                             f'{CO2.lower()}{prefix}')
            sensors.append(SensorMegaD(
                coordinator, port, unique_id_co2, CO2, prefix)
            )
            create_temp_hum(sensors, entry_id, coordinator, megad, port)
        if isinstance(port, I2CSensorMBx280):
            prefix = port.prefix
            unique_id_press = (f'{entry_id}-{megad.id}-{port.conf.id}-'
                               f'{PRESSURE}{prefix}')
            sensors.append(SensorMegaD(
                coordinator, port, unique_id_press, PRESSURE, prefix)
            )
            create_temp_hum(sensors, entry_id, coordinator, megad, port)
        if isinstance(port, I2CSensorINA226):
            prefix = port.prefix
            unique_id_current = (f'{entry_id}-{megad.id}-{port.conf.id}-'
                                 f'{CURRENT}{prefix}')
            sensors.append(SensorMegaD(
                coordinator, port, unique_id_current, CURRENT, prefix)
            )
            unique_id_voltage = (f'{entry_id}-{megad.id}-{port.conf.id}-'
                                 f'{VOLTAGE}{prefix}')
            sensors.append(SensorMegaD(
                coordinator, port, unique_id_voltage, VOLTAGE, prefix)
            )
            unique_id_raw = (f'{entry_id}-{megad.id}-{port.conf.id}-'
                             f'{RAW_VALUE}{prefix}')
            sensors.append(SensorMegaD(
                coordinator, port, unique_id_raw, RAW_VALUE, prefix)
            )
        if isinstance(port, I2CSensorBH1750):
            prefix = port.prefix
            unique_id = (f'{entry_id}-{megad.id}-{port.conf.id}-'
                         f'{LUXURY}{prefix}')
            sensors.append(SensorMegaD(
                coordinator, port, unique_id, LUXURY, prefix)
            )
        if isinstance(port, I2CSensorT67xx):
            prefix = port.prefix
            unique_id = (f'{entry_id}-{megad.id}-{port.conf.id}-'
                         f'{LUXURY}{prefix}')
            sensors.append(SensorMegaD(
                coordinator, port, unique_id, CO2, prefix)
            )
        if isinstance(port, I2CSensorBMP180):
            prefix = port.prefix
            unique_id_temp = (f'{entry_id}-{megad.id}-{port.conf.id}-'
                              f'{TEMPERATURE}{prefix}')
            sensors.append(SensorMegaD(
                coordinator, port, unique_id_temp, TEMPERATURE, prefix)
            )
            unique_id_press = (f'{entry_id}-{megad.id}-{port.conf.id}-'
                               f'{PRESSURE}{prefix}')
            sensors.append(SensorMegaD(
                coordinator, port, unique_id_press, PRESSURE, prefix)
            )
        if isinstance(port, AnalogSensor):
            unique_id = f'{entry_id}-{megad.id}-{port.conf.id}-analog'
            sensors.append(AnalogSensorMegaD(coordinator, port, unique_id))

    sensors.append(SensorDeviceMegaD(
        coordinator, f'{entry_id}-{megad.id}-{TEMPERATURE}', TEMPERATURE)
    )
    sensors.append(SensorDeviceMegaD(
        coordinator, f'{entry_id}-{megad.id}-{UPTIME}', UPTIME)
    )
    for pid in megad.pids:
        unique_id = f'{entry_id}-{megad.id}-{pid.conf.id}-pid-value'
        sensors.append(PIDSensorMegaD(coordinator, pid, unique_id))

    for sensor in sensors:
        hass.data[DOMAIN][CURRENT_ENTITY_IDS][entry_id].append(
            sensor.unique_id)
    if sensors:
        async_add_entities(sensors)
        _LOGGER.debug(f'Добавлены сенсоры: {sensors}')


class StringSensorMegaD(CoordinatorEntity, SensorEntity):
    """Класс для сенсоров с текстовым значением"""

    def __init__(
            self, coordinator: MegaDCoordinator, port,
            unique_id: str
    ) -> None:
        super().__init__(coordinator)
        self._megad: MegaD = coordinator.megad
        self._port = port
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

    @property
    def native_value(self) -> str:
        """Возвращает состояние сенсора"""
        return self._port.state


class ReaderSensorMegaD(StringSensorMegaD):

    _attr_icon = 'mdi:lock-smart'


class ClickSensorMegaD(StringSensorMegaD):

    _attr_icon = 'mdi:gesture-tap-button'

    @cached_property
    def capability_attributes(self):
        return {
            "options": STATE_BUTTON
        }


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


class SensorMegaD(CoordinatorEntity, SensorEntity):

    def __init__(
            self, coordinator: MegaDCoordinator, port: DigitalSensorBase,
            unique_id: str, type_sensor: str, prefix: str = ''
    ) -> None:
        super().__init__(coordinator)
        self._megad: MegaD = coordinator.megad
        self._port: DigitalSensorBase = port
        self.type_sensor = type_sensor
        self._sensor_name: str = (f'{port.conf.name} '
                                  f'{TYPE_SENSOR_RUS[type_sensor]}{prefix}')
        self._unique_id: str = unique_id
        self._attr_device_info = coordinator.devices_info()
        self.entity_id = (f'sensor.{self._megad.id}_port{port.conf.id}_'
                          f'{self.type_sensor.lower()}{prefix}')
        self.last_value: None | int | float = None
        self.info_filter()

    def __repr__(self) -> str:
        if not self.hass:
            return f"<Sensor entity {self.entity_id}>"
        return super().__repr__()

    def info_filter(self):
        """Вывод информации в лог при включенной фильтрации сенсора."""
        if self._port.conf.filter:
            _LOGGER.info(f'Включена фильтрация значения у сенсора '
                         f'{self.entity_id}')

    def general_filter(self, min_value, max_value, value, value_jump):
        """Общий фильтр значений сенсоров."""
        if value < min_value: value = min_value
        elif value > max_value: value = max_value
        if self.last_value is not None:
            if value in (min_value, max_value) and (
                    abs(value - self.last_value) > value_jump):
                return self.last_value
            elif value == 0 and abs(self.last_value) > value_jump:
                return self.last_value
        self.last_value = value
        return value

    def filter_temperature(self, value):
        """Фильтр для значений температуры."""
        min_value, max_value = TEMPERATURE_CONDITION[
            self._port.conf.device_class
        ]
        min_value -= DEVIATION_TEMPERATURE
        max_value += DEVIATION_TEMPERATURE
        return self.general_filter(
            min_value, max_value, value, ALLOWED_TEMP_JUMP
        )

    def filter_humidity(self, value):
        """Фильтр для значений влажности."""
        min_value, max_value = 0, 100
        return self.general_filter(
            min_value, max_value, value, ALLOWED_HUM_JUMP
        )

    def filter_bad_value(self, value):
        """Фильтрация неадекватных значений сенсоров."""
        if self._port.conf.filter:
            try:
                value = float(value)
            except (ValueError, TypeError):
                pass
            if not isinstance(value, float):
                return self.last_value
            match self.type_sensor:
                case TYPE_SENSOR.TEMPERATURE:
                    return self.filter_temperature(value)
                case TYPE_SENSOR.HUMIDITY:
                    return self.filter_humidity(value)
                case _:
                    self.last_value = value
                    return value
        else:
            return value

    @cached_property
    def name(self) -> str:
        return self._sensor_name

    @cached_property
    def unique_id(self) -> str:
        return self._unique_id

    @cached_property
    def state_class(self) -> SensorStateClass | str | None:
        """Return the state class of this entity, if any."""
        return SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | str:
        """Возвращает состояние сенсора"""
        value = self._port.state.get(self.type_sensor)
        return self.filter_bad_value(value)

    @cached_property
    def native_unit_of_measurement(self) -> str | None:
        """Возвращает единицу измерения сенсора"""
        return SENSOR_UNIT.get(self.type_sensor)

    @cached_property
    def device_class(self) -> str | None:
        return SENSOR_CLASS.get(self.type_sensor)


class SensorBusMegaD(SensorMegaD):

    def __init__(
            self, coordinator: MegaDCoordinator, port: DigitalSensorBase,
            unique_id: str, type_sensor: str, id_one_wire: str
    ) -> None:
        super().__init__(coordinator, port, unique_id, type_sensor)
        self.id_one_wire = id_one_wire
        self._sensor_name: str = f'{port.conf.name}_{id_one_wire}'
        self._unique_id: str = unique_id
        self.entity_id = (f'sensor.{self._megad.id}_port{port.conf.id}_'
                          f'{id_one_wire}')

    @property
    def native_value(self) -> float | str:
        """Возвращает состояние сенсора"""
        value = self._port.state.get(self.id_one_wire)
        return self.filter_bad_value(value)


class SensorDeviceMegaD(CoordinatorEntity, SensorEntity):

    def __init__(
            self, coordinator: MegaDCoordinator, unique_id: str,
            type_sensor: str
    ) -> None:
        super().__init__(coordinator)
        self._megad: MegaD = coordinator.megad
        self.type_sensor = type_sensor
        self._sensor_name: str = f'megad_{self._megad.id}_{type_sensor}'
        self._unique_id: str = unique_id
        self._attr_device_info = coordinator.devices_info()
        self.entity_id = f'sensor.megad_{self._sensor_name}'

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
    def state_class(self) -> SensorStateClass | str | None:
        """Return the state class of this entity, if any."""
        return SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | str:
        """Возвращает состояние сенсора"""
        if self.type_sensor == TEMPERATURE:
            return self._megad.temperature
        elif self.type_sensor == UPTIME:
            return self._megad.uptime

    @cached_property
    def native_unit_of_measurement(self) -> str | None:
        """Возвращает единицу измерения сенсора"""
        return SENSOR_UNIT.get(self.type_sensor)

    @cached_property
    def device_class(self) -> str | None:
        return SENSOR_CLASS.get(self.type_sensor)


class AnalogSensorMegaD(CoordinatorEntity, SensorEntity):

    _attr_icon = 'mdi:alpha-a-circle-outline'

    def __init__(
            self, coordinator: MegaDCoordinator, port: AnalogSensor,
            unique_id: str, type_sensor: str | None = None
    ) -> None:
        super().__init__(coordinator)
        self._megad: MegaD = coordinator.megad
        self._port: AnalogSensor = port
        self.type_sensor = type_sensor
        self._sensor_name: str = port.conf.name
        self._unique_id: str = unique_id
        self._attr_device_info = coordinator.devices_info()
        self.entity_id = f'sensor.{self._megad.id}_port{port.conf.id}_analog'

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
    def state_class(self) -> SensorStateClass | str | None:
        """Return the state class of this entity, if any."""
        return SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | str:
        """Возвращает состояние сенсора"""
        return self._port.state


class PIDSensorMegaD(CoordinatorEntity, SensorEntity):

    _attr_icon = 'mdi:information-outline'

    def __init__(
            self, coordinator: MegaDCoordinator, pid: PIDControl,
            unique_id: str, type_sensor: str | None = None
    ) -> None:
        super().__init__(coordinator)
        self._megad: MegaD = coordinator.megad
        self._pid: PIDControl = pid
        self.type_sensor = type_sensor
        self._attr_name = f'{self._megad.id}_{pid.conf.id}_pid_value'
        self._attr_unique_id = unique_id
        self._attr_device_info = coordinator.devices_info()

    def __repr__(self) -> str:
        if not self.hass:
            return f"<Sensor entity {self.entity_id}>"
        return super().__repr__()

    @cached_property
    def state_class(self) -> SensorStateClass | str | None:
        """Return the state class of this entity, if any."""
        return SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Возвращает состояние сенсора"""
        if self._pid.value is not None:
            return int(self._pid.value)
        else:
            return 0

    @cached_property
    def extra_state_attributes(self):
        """Дополнительные атрибуты сенсора."""
        return {
            'min_value': -32767,
            'max_value': 32767,
        }
