import asyncio
import logging
import time
from typing import Any

from propcache import cached_property

from homeassistant.components.update import UpdateEntity, UpdateDeviceClass, \
    UpdateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from . import MegaDCoordinator
from .const import RELEASE_URL, DOMAIN, ENTRIES, CURRENT_ENTITY_IDS
from .core.megad import MegaD


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback
) -> None:
    entry_id = config_entry.entry_id
    coordinator = hass.data[DOMAIN][ENTRIES][entry_id]

    firmware_update_entity = MegaDFirmwareUpdate(coordinator)
    hass.data[DOMAIN][CURRENT_ENTITY_IDS][entry_id].append(
        firmware_update_entity.unique_id
    )

    if firmware_update_entity:
        async_add_entities([firmware_update_entity])
        _LOGGER.debug(f'Добавлена сущность обновления контроллера: {firmware_update_entity}')


class MegaDFirmwareUpdate(CoordinatorEntity, UpdateEntity):
    """Представляет сущность для обновления прошивки MegaD."""

    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_has_entity_name = True
    _attr_release_url: str | None = RELEASE_URL
    _attr_supported_features = UpdateEntityFeature.INSTALL | UpdateEntityFeature.RELEASE_NOTES

    def __init__(self, coordinator: MegaDCoordinator):
        super().__init__(coordinator)
        self._megad: MegaD = coordinator.megad
        self._attr_unique_id = f'{self._megad.id}-megad_firmware_update'
        self._attr_name = 'Обновление прошивки контроллера'
        self._current_version = self._megad.software
        self._latest_version = self._megad.software_latest
        self._attr_device_info = coordinator.devices_info()
        self.entity_id = f'update.{self._megad.id}-megad_firmware_update'

    @property
    def installed_version(self):
        """Version installed and in use."""
        return self._current_version

    @property
    def latest_version(self):
        """Latest version available for install."""
        return self._latest_version

    @cached_property
    def release_summary(self) -> str | None:
        """Summary of the release notes or changelog."""
        return 'Короткое содержание описания прошивки'

    @cached_property
    def title(self) -> str | None:
        """Title of the software.
        """
        return f'IP-адрес устройства: {self._megad.id}'

    def release_notes(self) -> str | None:
        """Return full release notes."""
        return 'Это самая лучшая версия прошивки. Устройство может творить чудеса.'

    def version_is_newer(self, latest_version: str, installed_version: str) -> bool:
        """Return True if latest_version is newer than installed_version."""
        return bool(self._latest_version > self._current_version)

    @cached_property
    def release_url(self) -> str | None:
        """URL to the full release notes of the latest version available."""
        return self._attr_release_url

    # async def async_install(self, version, backup=False):
    #     """Имитация обновления прошивки."""
    #     # Логируем, что обновление началось
    #
    #     _LOGGER.info(f"Обновление прошивки до версии {version}...")
    #
    #     # Имитируем задержку обновления
    #     await asyncio.sleep(5)
    #
    #     # Обновляем installed_version
    #     self._current_version = version
    #     _LOGGER.info(f"Прошивка успешно обновлена до версии {version}.")

    def install(self, version: str | None, backup: bool = False, **kwargs: Any) -> None:
        """Install an update.

        Version can be specified to install a specific version. When `None`, the
        latest version needs to be installed.

        The backup parameter indicates a backup should be taken before
        installing the update.
        """
        _LOGGER.info(f'Обновляю прошивку!!!!!{version}')
        time.sleep(5)
        self._current_version = self.latest_version

    # async def async_install(self, version, backup):
    #     """Устанавливает новую версию прошивки."""
    #     _LOGGER.info(f'Обновляю прошивку!!!!!{version}')
    #     # await self._update_callback(version)