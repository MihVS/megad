import asyncio
import logging
from datetime import timedelta

import async_timeout

from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.config_entries import ConfigEntry
from .const import (
    TIME_UPDATE, DOMAIN, MANUFACTURER, TIME_OUT_UPDATE_DATA, COUNTER_CONNECT,
    PLATFORMS
)
from .core.config_parser import create_config_megad
from .core.enums import ModeInMegaD
from .core.megad import MegaD
from .core.models_megad import DeviceMegaD
from .core.server import MegadHttpView
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator, UpdateFailed
)


_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Регистрируем HTTP ручку"""
    hass.http.register_view(MegadHttpView())
    return True


def remove_entity(
        hass: HomeAssistant, megad: MegaD, config_entry: ConfigEntry):
    """Удаление неиспользуемых сущностей"""
    entity_registry = async_get_entity_registry(hass)

    # _LOGGER.warning(entity_registry.entities)
    count = 0
    for entity_id, entity in entity_registry.entities.items():
        _LOGGER.info(entity_id)
        _LOGGER.info(entity)
        # _LOGGER.warning(entity.config_entry_id)
        # _LOGGER.warning(config_entry.entry_id)
        if entity.config_entry_id == config_entry.entry_id:
            count += 1
            _LOGGER.debug(entity_id)
    _LOGGER.info(count)


    # entities = entity_registry.entities
    # _LOGGER.info(f'Сущности связанные с {config_entry}: {entities}')
    # active_entity = megad.ports
    # _LOGGER.info(f'Активные порты: {active_entity}')



    # entity_registry = async_get_entity_registry(hass)
    # # device_registry = async_get_device_registry(hass)
    # current_entities = {
    #     obj.platform.domain + '.' + obj.unique_id.lower().replace("-", "_") for
    #     hub_id, entities in hass.data[DOMAIN].get("ports", {}).items() for obj
    #     in entities}
    # _LOGGER.debug("Current unique IDs: %s", current_entities)
    # all_entities = {
    #     entity_id: entity
    #     for entity_id, entity in entity_registry.entities.items()
    #     if entity.config_entry_id == config_entry.entry_id
    # }
    # entities_to_remove = [
    #     entity_id
    #     for entity_id, entity in all_entities.items()
    #     if entity_id not in current_entities
    # ]
    #
    # _LOGGER.debug("Entities to remove: %s", entities_to_remove)


async def async_setup_entry(
        hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    config_entry.async_on_unload(
        config_entry.add_update_listener(update_listener)
    )
    entry_id = config_entry.entry_id
    _LOGGER.debug(f'Entry_id {entry_id}')
    file_path = config_entry.data.get('file_path')
    megad_config = await create_config_megad(file_path)
    megad = MegaD(hass=hass, config=megad_config)
    coordinator = MegaDCoordinator(hass=hass, megad=megad)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry_id] = coordinator

    remove_entity(hass, megad, config_entry)

    await hass.config_entries.async_forward_entry_setups(
        config_entry, PLATFORMS
    )
    remove_entity(hass, megad, config_entry)
    return True


async def update_listener(hass, entry):
    """Вызывается при изменении настроек интеграции."""
    await hass.config_entries.async_reload(entry.entry_id)


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
            async with async_timeout.timeout(TIME_OUT_UPDATE_DATA):
                await self.megad.update_data()
                return self.megad
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
                raise UpdateFailed(f"Ошибка соединения с контроллером id: "
                                   f"{self.megad.config.plc.megad_id}: {err}")

    async def _turn_off_state(self, state_off, delay, port_id, data):
        """Возвращает выключенное состояние порта"""
        self.megad.update_port(port_id, data)
        self.async_set_updated_data(self.megad)
        await asyncio.sleep(delay)
        self.megad.update_port(port_id, state_off)
        self.async_set_updated_data(self.megad)

    async def update_port_state(self, port_id, data):
        """Обновление состояния конкретного порта."""
        port = self.megad.get_port(port_id)
        if port is None:
            return
        if port.conf.mode == ModeInMegaD.C:
            await self._turn_off_state('off', 0.5, port_id, data)
        else:
            self.megad.update_port(port_id, data)
            self.async_set_updated_data(self.megad)

    def update_group_state(self, port_states: dict[int, str]):
        """Обновление состояний портов в группе"""

        for port_id, state in port_states.items():
            self.megad.update_port(port_id, state)
        self.async_set_updated_data(self.megad)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    _LOGGER.info(f'Выгрузка интеграции: {entry.entry_id}')
    _LOGGER.info(f'data: {entry.data}')
    try:
        unload_ok = await hass.config_entries.async_unload_platforms(
            entry, PLATFORMS
        )
        hass.data[DOMAIN].pop(entry.entry_id)

        return unload_ok
    except Exception as e:
        _LOGGER.error(f'Ошибка при выгрузке: {e}')
        return False
