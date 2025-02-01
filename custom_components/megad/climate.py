"""
Нужно подумать как отслеживать статус включеного состояния и отключеного.
И не забыть про инверсию (нагрев или охлаждение)
Можно это делать по управляемому порту, а лучше ловить ответ от контроллера
и менять статус.
Условие создание термостата настройки поля Mode и галочка поля Action
Не забыть реализовать восстановление заданной температуры после перезагрузки
"""
import asyncio
import logging

from propcache import cached_property

from homeassistant.components.climate import (
    HVACMode, ClimateEntity, ClimateEntityFeature, HVACAction, PRESET_NONE
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from . import MegaDCoordinator
from .const import (
    DOMAIN, ENTRIES, CURRENT_ENTITY_IDS, TEMPERATURE_CONDITION, TEMPERATURE,
    OFF, ON
)
from .core.base_ports import OneWireSensorPort
from .core.enums import ModeSensorMegaD
from .core.exceptions import TemperatureOutOfRangeError
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

    thermostats = []
    for port in megad.ports:
        if isinstance(port, OneWireSensorPort):
            if (
                    port.conf.mode == ModeSensorMegaD.LESS_AND_MORE
                    and port.conf.execute_action
            ):
                unique_id = f'{entry_id}-{megad.id}-{port.conf.id}-climate'
                thermostats.append(OneWireClimateEntity(
                    coordinator, port, unique_id)
                )
    for thermostat in thermostats:
        hass.data[DOMAIN][CURRENT_ENTITY_IDS][entry_id].append(
            thermostat.unique_id)
    if thermostats:
        async_add_entities(thermostats)
        _LOGGER.debug(f'Добавлены термостаты: {thermostats}')


class OneWireClimateEntity(CoordinatorEntity, ClimateEntity):
    """Нагревательный терморегулятор"""

    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_min_temp = 0
    _attr_max_temp = 40
    _attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE |
            ClimateEntityFeature.PRESET_MODE
    )

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
    def hvac_mode(self) -> HVACMode | None:
        """Return hvac operation ie. heat, cool mode."""
        if self._port.status:
            return HVACMode.HEAT
        return HVACMode.OFF

    @property
    def temperature_unit(self):
        """Возвращает единицы измерения температуры."""
        return UnitOfTemperature.CELSIUS

    @property
    def target_temperature(self):
        """Возвращает целевую температуру."""
        return self._port.conf.set_value

    @property
    def current_temperature(self):
        """Возвращает текущую температуру."""
        return self._port.state[TEMPERATURE]

    @property
    def hvac_action(self):
        """Возвращает текущее действие HVAC (нагрев, охлаждение и т.д.)."""
        if not self._port.status:
            return HVACMode.HEAT
        return HVACMode.OFF

    async def async_set_hvac_mode(self, hvac_mode):
        """Устанавливает режим HVAC."""
        self._port.status = True if hvac_mode == HVACMode.HEAT else False
        if hvac_mode == HVACMode.OFF:
            await self._megad.set_port(self._port.conf.id, OFF)
        else:
            await self._megad.set_port(self._port.conf.id, ON)
        self.schedule_update_ha_state()

    async def async_set_temperature(self, **kwargs):
        """Устанавливает целевую температуру."""
        set_temp = kwargs.get('temperature')
        if self._attr_min_temp <= set_temp <= self._attr_max_temp:
            await self._megad.set_temperature(self._port.conf.id, set_temp)
            await self._coordinator.update_set_temperature(
                self._port.conf.id, set_temp
            )
        else:
            raise TemperatureOutOfRangeError(
                f'Недопустимое значение температуры: {set_temp}. '
                f'Задайте температуру в пределах от {self._attr_min_temp} '
                f'до {self._attr_max_temp} включительно.'
            )

