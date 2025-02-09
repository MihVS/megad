import logging

from propcache import cached_property

from homeassistant.components.climate import (
    HVACMode, ClimateEntity, ClimateEntityFeature, HVACAction
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from . import MegaDCoordinator
from .const import (
    DOMAIN, ENTRIES, CURRENT_ENTITY_IDS, TEMPERATURE_CONDITION, TEMPERATURE,
    OFF, ON, STATUS_THERMO, DIRECTION, PID_OFF
)
from .core.base_ports import OneWireSensorPort
from .core.enums import ModePIDMegaD
from .core.exceptions import TemperatureOutOfRangeError
from .core.megad import MegaD
from .core.models_megad import PIDConfig
from .core.utils import get_action_turnoff

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback
) -> None:
    entry_id = config_entry.entry_id
    coordinator = hass.data[DOMAIN][ENTRIES][entry_id]
    megad = coordinator.megad

    thermostats = []
    for port in megad.ports:
        if megad.check_port_is_thermostat(port):
            unique_id = f'{entry_id}-{megad.id}-{port.conf.id}-climate'
            if port.conf.inverse:
                thermostats.append(
                    CoolClimateEntity(coordinator, port, unique_id)
                )
            else:
                thermostats.append(
                    HeatClimateEntity(coordinator, port, unique_id)
                )
    for pid in megad.pids:
        unique_id = f'{entry_id}-{megad.id}-{pid.id}-pid'
        port_in = megad.get_port(pid.sensor_id)
        thermostats.append(
            PIDClimateEntity(coordinator, pid, port_in, unique_id)
        )

    for thermostat in thermostats:
        hass.data[DOMAIN][CURRENT_ENTITY_IDS][entry_id].append(
            thermostat.unique_id)
    if thermostats:
        async_add_entities(thermostats)
        _LOGGER.debug(f'Добавлены термостаты: {thermostats}')


class BaseClimateEntity(CoordinatorEntity, ClimateEntity):
    """Базовый класс терморегулятора"""

    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

    def __init__(
            self, coordinator: MegaDCoordinator, port: OneWireSensorPort,
            unique_id: str
    ) -> None:
        super().__init__(coordinator)
        self._coordinator: MegaDCoordinator = coordinator
        self._megad: MegaD = coordinator.megad
        self._port: OneWireSensorPort = port
        self._name: str = port.conf.name
        self._unique_id: str = unique_id
        self._attr_device_info = coordinator.devices_info()
        self.entity_id = f'climate.{self._megad.id}_port{port.conf.id}'
        self._attr_min_temp, self._attr_max_temp = (
            TEMPERATURE_CONDITION[port.conf.device_class]
        )

    def __repr__(self) -> str:
        if not self.hass:
            return f"<Thermostat entity {self.entity_id}>"
        return super().__repr__()

    @cached_property
    def name(self) -> str:
        return self._name

    @cached_property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def temperature_unit(self):
        """Возвращает единицы измерения температуры."""
        return UnitOfTemperature.CELSIUS

    @property
    def target_temperature(self):
        """Возвращает целевую температуру."""
        if self._port.state.get(STATUS_THERMO):
            return float(self._port.conf.set_value)

    @property
    def current_temperature(self):
        """Возвращает текущую температуру."""
        return float(self._port.state[TEMPERATURE])

    async def async_set_hvac_mode(self, hvac_mode):
        """Устанавливает режим HVAC."""
        if hvac_mode in (HVACMode.HEAT, HVACMode.COOL):
            await self._megad.set_port(self._port.conf.id, ON)
            await self._coordinator.update_port_state(
                self._port.conf.id, {STATUS_THERMO: True}
            )
        else:
            await self._megad.set_port(self._port.conf.id, OFF)
            actions_off = get_action_turnoff(self._port.conf.action)
            await self._megad.send_command(actions_off)
            for action in actions_off.split(';'):
                if action:
                    port_id, state = action.split(':')
                    await self._coordinator.update_port_state(port_id, state)
            if HVACMode.COOL in self._attr_hvac_modes:
                await self._coordinator.update_port_state(
                    self._port.conf.id, {DIRECTION: False}
                )
            else:
                await self._coordinator.update_port_state(
                    self._port.conf.id, {DIRECTION: True}
                )
            await self._coordinator.update_port_state(
                self._port.conf.id, {STATUS_THERMO: False}
            )

    async def async_set_temperature(self, **kwargs):
        """Устанавливает целевую температуру."""
        set_temp = kwargs.get('temperature')
        if self._attr_min_temp <= set_temp <= self._attr_max_temp:
            await self._megad.set_temperature(self._port.conf.id, set_temp)
            self._coordinator.update_set_temperature(
                self._port.conf.id, set_temp
            )
        else:
            raise TemperatureOutOfRangeError(
                f'Недопустимое значение температуры: {set_temp}. '
                f'Задайте температуру в пределах от {self._attr_min_temp} '
                f'до {self._attr_max_temp} включительно.'
            )


class HeatClimateEntity(BaseClimateEntity):
    """Нагревательный терморегулятор"""

    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return hvac operation ie. heat, cool mode."""
        status = self._port.state.get(STATUS_THERMO)
        if status:
            return HVACMode.HEAT
        return HVACMode.OFF

    @property
    def hvac_action(self):
        """Возвращает текущее действие HVAC (нагрев, охлаждение и т.д.)."""
        if self._port.state.get(STATUS_THERMO):
            direction = self._port.state.get(DIRECTION)
            if not direction:
                return HVACAction.HEATING
            return HVACAction.IDLE
        else:
            return HVACAction.OFF


class CoolClimateEntity(BaseClimateEntity):
    """Охладительный терморегулятор"""

    _attr_hvac_modes = [HVACMode.COOL, HVACMode.OFF]

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return hvac operation ie. heat, cool mode."""
        status = self._port.state.get(STATUS_THERMO)
        if status:
            return HVACMode.COOL
        return HVACMode.OFF

    @property
    def hvac_action(self):
        """Возвращает текущее действие HVAC (нагрев, охлаждение и т.д.)."""
        if self._port.state.get(STATUS_THERMO):
            direction = self._port.state.get(DIRECTION)
            if direction:
                return HVACAction.COOLING
            return HVACAction.IDLE
        else:
            return HVACAction.OFF


class PIDClimateEntity(BaseClimateEntity):
    """Базовый класс для терморегулятора с ПИД регулированием"""

    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

    def __init__(
            self, coordinator: MegaDCoordinator, pid: PIDConfig,
            port: OneWireSensorPort, unique_id: str
    ) -> None:
        super().__init__(coordinator, port, unique_id)
        self._pid: PIDConfig = pid
        self._name: str = pid.name
        self.entity_id = f'climate.{self._megad.id}_pid{pid.id}'
        self._attr_min_temp, self._attr_max_temp = (
            TEMPERATURE_CONDITION[pid.device_class]
        )
        self._attr_hvac_modes = self.get_hvac_modes()

    def get_hvac_modes(self) -> list[HVACMode]:
        """Получить нужные режимы для терморегулятора"""
        if self._pid.mode == ModePIDMegaD.COOL:
            return [HVACMode.COOL, HVACMode.OFF]
        if self._pid.mode == ModePIDMegaD.HEAT:
            return [HVACMode.HEAT, HVACMode.OFF]
        return [HVACMode.AUTO, HVACMode.OFF]

    @property
    def target_temperature(self):
        """Возвращает целевую температуру."""
        return self._pid.set_point

    async def async_set_hvac_mode(self, hvac_mode):
        """Устанавливает режим HVAC."""
        if hvac_mode in (HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO):
            await self._megad.turn_on_pid(self._pid.id)
            self._coordinator.update_pid_state(
                self._pid.id, {'input': self._pid.sensor_id}
            )
        else:
            await self._megad.turn_off_pid(self._pid.id)
            self._coordinator.update_pid_state(
                self._pid.id, {'input': PID_OFF}
            )

    async def async_set_temperature(self, **kwargs):
        """Устанавливает целевую температуру."""
        set_temp = kwargs.get('temperature')
        if self._attr_min_temp <= set_temp <= self._attr_max_temp:
            await self._megad.set_temperature_pid(self._pid.id, set_temp)
            self._coordinator.update_pid_state(
                self._pid.id, {'set_point': set_temp}
            )
        else:
            raise TemperatureOutOfRangeError(
                f'Недопустимое значение температуры: {set_temp}. '
                f'Задайте температуру в пределах от {self._attr_min_temp} '
                f'до {self._attr_max_temp} включительно.'
            )

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return hvac operation ie. heat, cool mode."""
        if self._pid.input == PID_OFF:
            return HVACMode.OFF
        match self._pid.mode:
            case ModePIDMegaD.HEAT:
                return HVACMode.HEAT
            case ModePIDMegaD.COOL:
                return HVACMode.COOL
            case ModePIDMegaD.BALANCE:
                return HVACMode.AUTO
            case _:
                return HVACMode.OFF


    @property
    def hvac_action(self):
        """Возвращает текущее действие HVAC (нагрев, охлаждение и т.д.)."""
        if self._pid.input == PID_OFF:
            return HVACAction.OFF
        port_out = self._megad.get_port(self._pid.output)
        if port_out.state:
            return HVACAction.HEATING
        return HVACAction.IDLE
