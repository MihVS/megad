import asyncio
import logging
from datetime import timedelta

import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_registry import async_get
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator, UpdateFailed
)
from .const import (
    TIME_UPDATE, DOMAIN, MANUFACTURER, COUNTER_CONNECT, PLATFORMS, ENTRIES,
    CURRENT_ENTITY_IDS, STATUS_THERMO, TIME_SLEEP_REQUEST, OFF,
    FIRMWARE_CHECKER, TIME_OUT_UPDATE_DATA_GENERAL
)
from .core.base_ports import OneWireSensorPort, ReaderPort
from .core.config_manager import MegaDConfigManager
from .core.enums import ModeInMegaD, TypePortMegaD
from .core.exceptions import InvalidSettingPort, FirmwareUpdateInProgress
from .core.megad import MegaD
from .core.models_megad import DeviceMegaD, PIDConfig
from .core.request_to_ablogru import FirmwareChecker
from .core.server import MegadHttpView
from .core.utils import get_action_turnoff

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema("megad")


async def async_setup(hass: HomeAssistant, config: dict):
    """Регистрируем HTTP ручку"""
    hass.http.register_view(MegadHttpView())
    return True


def remove_entity(hass: HomeAssistant, current_entries_id: list,
                  config_entry: ConfigEntry):
    """Удаление неиспользуемых сущностей"""
    entity_registry = async_get(hass)
    remove_entities = []
    for entity_id, entity in entity_registry.entities.items():
        if entity.config_entry_id == config_entry.entry_id:
            if entity.unique_id not in current_entries_id:
                remove_entities.append(entity_id)
    for entity_id in remove_entities:
        entity_registry.async_remove(entity_id)
        _LOGGER.info(f'Удалена устаревшая сущность {entity_id}')


async def async_setup_entry(
        hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    config_entry.async_on_unload(
        config_entry.add_update_listener(update_listener)
    )
    entry_id = config_entry.entry_id
    _LOGGER.debug(f'Entry_id {entry_id}')
    file_path = config_entry.data.get('file_path')
    url = config_entry.data.get('url')
    manager_config = MegaDConfigManager(
        url, file_path, async_get_clientsession(hass)
    )
    await manager_config.read_config_file(file_path)
    megad_config = await manager_config.create_config_megad()
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(FIRMWARE_CHECKER, {})
    hass.data[DOMAIN].setdefault(ENTRIES, {})
    hass.data[DOMAIN][ENTRIES][entry_id] = None
    if not hass.data[DOMAIN][FIRMWARE_CHECKER]:
        fw_checker = FirmwareChecker(hass)
        await fw_checker.update_page_firmwares()
        hass.data[DOMAIN][FIRMWARE_CHECKER] = fw_checker
        _LOGGER.debug(f'Добавлен firmware checker: '
                      f'{hass.data[DOMAIN][FIRMWARE_CHECKER]}')
    megad = MegaD(
        hass=hass,
        config=megad_config,
        url=url,
        config_path=file_path,
        fw_checker=hass.data[DOMAIN][FIRMWARE_CHECKER]
    )
    await megad.async_init_i2c_bus()

    coordinator = MegaDCoordinator(hass=hass, megad=megad)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN].setdefault(CURRENT_ENTITY_IDS, {})
    hass.data[DOMAIN][CURRENT_ENTITY_IDS][entry_id] = []
    hass.data[DOMAIN][ENTRIES][entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(
        config_entry, PLATFORMS
    )
    current_entries_id = hass.data[DOMAIN][CURRENT_ENTITY_IDS][entry_id]
    remove_entity(hass, current_entries_id, config_entry)
    _LOGGER.debug(f'Unique_id актуальных сущностей контроллера {megad.id}: '
                  f'{current_entries_id}')
    _LOGGER.debug(f'Количество актуальных сущностей: '
                  f'{len(current_entries_id)}')
    return True


async def update_listener(hass, entry):
    """Вызывается при изменении настроек интеграции."""
    _LOGGER.info(f'Перезапуск интеграции для entry_id: {entry.entry_id})')
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    _LOGGER.info(f'Выгрузка интеграции: {entry.entry_id}')
    _LOGGER.info(f'data: {entry.data}')
    try:
        unload_ok = await hass.config_entries.async_unload_platforms(
            entry, PLATFORMS
        )
        hass.data[DOMAIN][ENTRIES].pop(entry.entry_id)

        return unload_ok
    except Exception as e:
        _LOGGER.error(f'Ошибка при выгрузке: {e}')
        return False


class MegaDCoordinator(DataUpdateCoordinator):
    """Координатор для общего обновления данных"""

    _count_connect: int = 0

    def __init__(self, hass, megad):
        super().__init__(
            hass,
            _LOGGER,
            name=f'MegaD Coordinator id: {megad.id}',
            update_interval=timedelta(seconds=TIME_UPDATE),
        )
        self.megad: MegaD = megad

    def devices_info(self):
        megad_id = self.megad.config.plc.megad_id
        device_info = DeviceInfo(**{
            "identifiers": {(DOMAIN, megad_id)},
            "name": f'MegaD-{megad_id}',
            "sw_version": self.megad.software,
            "configuration_url": self.megad.url,
            "manufacturer": MANUFACTURER,
        })
        return device_info

    async def _async_update_data(self):
        """Обновление всех данных megad"""
        try:
            if self.megad.is_flashing:
                raise FirmwareUpdateInProgress
            async with async_timeout.timeout(TIME_OUT_UPDATE_DATA_GENERAL):
                await self.megad.update_data()
                return self.megad
        except FirmwareUpdateInProgress:
            _LOGGER.warning(f'Обновление данных недоступно, контроллер '
                            f'id-{self.megad.id} обновляется.')
            raise UpdateFailed(f'Идёт процесс обновления ПО MegaD id: '
                               f'{self.megad.config.plc.megad_id}')
        except Exception as err:
            if self._count_connect < COUNTER_CONNECT:
                self._count_connect += 1
                _LOGGER.warning(
                    f'Неудачная попытка обновления данных контроллера '
                    f'id: {self.megad.config.plc.megad_id}. Ошибка: {err}.'
                    f'Осталось попыток: '
                    f'{COUNTER_CONNECT - self._count_connect}'
                )
                return self.megad
            else:
                raise UpdateFailed(f'Ошибка соединения с контроллером id: '
                                   f'{self.megad.config.plc.megad_id}: {err}')

    async def set_flashing_state(self, state):
        """Устанавливает режим прошивки устройства."""
        self.megad.is_flashing = state
        self.hass.loop.call_soon(self.async_update_listeners)
        self.last_update_success = not state

    async def _turn_off_state(self, state_off, delay, port_id, data):
        """Возвращает выключенное состояние порта."""
        self.megad.update_port(port_id, data)
        self.hass.loop.call_soon(self.async_update_listeners)
        await asyncio.sleep(delay)
        self.megad.update_port(port_id, state_off)
        self.hass.loop.call_soon(self.async_update_listeners)

    def update_pid_state(self, pid_id: int, data: dict):
        """Обновление состояния ПИД регулятора."""
        self.megad.update_pid(pid_id, data)
        self.hass.loop.call_soon(self.async_update_listeners)

    async def update_port_state(self, port_id, data, ext=False):
        """Обновление состояния конкретного порта."""
        if ext:
            port_ext = self.megad.get_port(port_id, ext=ext)
            if port_ext is None:
                pass
            elif port_ext.conf.interrupt is not None:
                self.megad.update_port(port_ext.conf.id, data)
        port = self.megad.get_port(port_id)
        if port is None:
            return
        if port.conf.type_port in (TypePortMegaD.ADC, ):
            return
        if isinstance(port, ReaderPort) or port.conf.mode == ModeInMegaD.C:
            await self._turn_off_state('off', 0.5, port_id, data)
        else:
            self.megad.update_port(port.conf.id, data)
            self.hass.loop.call_soon(self.async_update_listeners)

    def update_set_temperature(self, port_id, temperature):
        """Обновление заданной температуры порта сенсора"""
        port = self.megad.get_port(port_id)
        if isinstance(port, OneWireSensorPort):
            port.conf.set_value = temperature
            self.hass.loop.call_soon(self.async_update_listeners)
        else:
            raise InvalidSettingPort(f'Проверьте настройки порта №{port_id}')

    def update_group_state(self, port_states: dict[int, str]):
        """Обновление состояний портов в группе"""
        for port_id, state in port_states.items():
            self.megad.update_port(port_id, state)
        self.hass.loop.call_soon(self.async_update_listeners)

    async def restore_thermo(self, port):
        """Восстановление состояния терморегулятора после перезагрузки плк"""
        await self.megad.set_temperature(
            port.conf.id, port.conf.set_value
        )
        if not port.state[STATUS_THERMO]:
            await asyncio.sleep(TIME_SLEEP_REQUEST)
            await self.megad.set_port(port.conf.id, OFF)
            await self.megad.send_command(get_action_turnoff(port.conf.action))

    async def restore_status_ports(self):
        """Восстановление состояния портов после перезагрузки контроллера"""
        for port in self.megad.ports:
            if port.conf.type_port == TypePortMegaD.OUT:
                state = not port.state if port.conf.inverse else port.state
                await self.megad.set_port(port.conf.id, int(state))
            if self.megad.check_port_is_thermostat(port):
                await self.restore_thermo(port)
        await asyncio.sleep(1)
        await self.megad.update_data()
        self.hass.loop.call_soon(self.async_update_listeners)
