import logging
from datetime import timedelta

import async_timeout

from homeassistant.config_entries import ConfigEntry
from .const import (
    TIME_UPDATE, DOMAIN, MANUFACTURER, TIME_OUT_UPDATE_DATA, COUNTER_CONNECT,
    PLATFORMS
)
from .core.config_parser import create_config_megad
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


async def async_setup_entry(
        hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    entry_id = config_entry.entry_id
    _LOGGER.debug(f'Entry_id {entry_id}')
    file_path = config_entry.data.get('file_path')
    megad_config = await create_config_megad(file_path)
    megad = MegaD(hass=hass, config=megad_config)
    # await megad.update_data()
    _LOGGER.debug(megad)
    coordinator = MegaDCoordinator(hass, megad)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(
        config_entry, PLATFORMS
    )
    return True


class MegaDCoordinator(DataUpdateCoordinator):
    """Координатор для общего обновления данных"""

    _count_connect: int = 0

    def __init__(self, hass, megad):
        super().__init__(
            hass,
            _LOGGER,
            name="MegaD",
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
        """Обновление данных megad"""

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
                    f'Осталось попыток: {COUNTER_CONNECT - self._count_connect}'
                )
                return self.megad
            else:
                raise UpdateFailed(f"Ошибка соединения с контроллером id: "
                                   f"{self.megad.config.plc.megad_id}: {err}")
