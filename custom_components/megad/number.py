import logging

from propcache import cached_property

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from . import MegaDCoordinator
from .const import (
    DOMAIN, ENTRIES, CURRENT_ENTITY_IDS, STEP_FACTOR, P_FACTOR, I_FACTOR,
    D_FACTOR, PID_LIMIT_P, PID_LIMIT_I, PID_LIMIT_D, PID_P_FACTOR,
    PID_I_FACTOR, PID_D_FACTOR
)
from .core.base_pids import PIDControl
from .core.exceptions import SetFactorPIDError
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
    numbers = []
    for pid in megad.pids:
        unique_id_p = f'{entry_id}-{megad.id}-{pid.conf.id}-pid-p_factor'
        unique_id_i = f'{entry_id}-{megad.id}-{pid.conf.id}-pid-i_factor'
        unique_id_d = f'{entry_id}-{megad.id}-{pid.conf.id}-pid-d_factor'
        numbers.append(
            PIDCoefficientNumber(coordinator, pid, unique_id_p)
        )
        numbers.append(
            PIDCoefficientNumber(coordinator, pid, unique_id_i)
        )
        numbers.append(
            PIDCoefficientNumber(coordinator, pid, unique_id_d)
        )
    for number in numbers:
        hass.data[DOMAIN][CURRENT_ENTITY_IDS][entry_id].append(
            number.unique_id)
    if numbers:
        async_add_entities(numbers)
        _LOGGER.debug(f'Добавлены коэффициенты ПИД: {numbers}')


class PIDCoefficientNumber(CoordinatorEntity, NumberEntity):
    """Класс сущности для коэффициентов ПИД-регулятора."""

    def __init__(
            self, coordinator: MegaDCoordinator, pid: PIDControl,
            unique_id: str
    ):
        """Инициализация."""
        super().__init__(coordinator)
        self._coordinator: MegaDCoordinator = coordinator
        self._megad: MegaD = coordinator.megad
        self._pid = pid
        self.factor = unique_id[-8:]
        self._attr_name = f'{self._megad.id}_{pid.conf.id}_{self.factor}'
        self._attr_unique_id = unique_id
        self._attr_native_step = STEP_FACTOR
        self._attr_device_info = coordinator.devices_info()

    @cached_property
    def native_min_value(self) -> float:
        """Return the minimum value."""
        if P_FACTOR in self._attr_unique_id:
            return PID_LIMIT_P.min_value
        if I_FACTOR in self._attr_unique_id:
            return PID_LIMIT_I.min_value
        if D_FACTOR in self._attr_unique_id:
            return PID_LIMIT_D.min_value

    @cached_property
    def native_max_value(self) -> float:
        """Return the maximum value."""
        if P_FACTOR in self._attr_unique_id:
            return PID_LIMIT_P.max_value
        if I_FACTOR in self._attr_unique_id:
            return PID_LIMIT_I.max_value
        if D_FACTOR in self._attr_unique_id:
            return PID_LIMIT_D.max_value

    @property
    def native_value(self):
        """Возвращает текущее значение коэффициента."""
        if P_FACTOR in self._attr_unique_id:
            return self._pid.p
        if I_FACTOR in self._attr_unique_id:
            return self._pid.i
        if D_FACTOR in self._attr_unique_id:
            return self._pid.d

    async def async_set_native_value(self, value: float) -> None:
        """Устанавливает новое значение коэффициента."""
        try:
            if P_FACTOR in self._attr_unique_id:
                await self._megad.set_pid(
                    self._pid.conf.id, {PID_P_FACTOR: value}
                )
                self._coordinator.update_pid_state(
                    self._pid.conf.id, {P_FACTOR: value}
                )
            if I_FACTOR in self._attr_unique_id:
                await self._megad.set_pid(
                    self._pid.conf.id, {PID_I_FACTOR: value}
                )
                self._coordinator.update_pid_state(
                    self._pid.conf.id, {I_FACTOR: value}
                )
            if D_FACTOR in self._attr_unique_id:
                await self._megad.set_pid(
                    self._pid.conf.id, {PID_D_FACTOR: value}
                )
                self._coordinator.update_pid_state(
                    self._pid.conf.id, {D_FACTOR: value}
                )
        except Exception as e:
            raise SetFactorPIDError(f'MegaD-{self._megad.id}, ПИД '
                                    f'№{self._pid.conf.id}: не удалось '
                                    f'изменить коэффициент {self.factor}. '
                                    f'Ошибка: {e}')
