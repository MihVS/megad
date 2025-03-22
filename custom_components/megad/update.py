import asyncio
import logging
import socket
import time
import requests
from typing import Any

from propcache import cached_property

from homeassistant.components.network import async_get_source_ip
from homeassistant.components.update import (
    UpdateEntity, UpdateDeviceClass, UpdateEntityFeature
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from . import MegaDCoordinator
from .const import (
    RELEASE_URL, DOMAIN, ENTRIES, CURRENT_ENTITY_IDS
)
from .core.const_fw import RECV_TIMEOUT
from .core.exceptions import CreateSocketReceiveError, CreateSocketSendError
from .core.megad import MegaD
from .core.utils import create_receive_socket, create_send_socket

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
        _LOGGER.debug(f'Добавлена сущность обновления контроллера: '
                      f'{firmware_update_entity}')


class MegaDFirmwareUpdate(CoordinatorEntity, UpdateEntity):
    """Представляет сущность для обновления прошивки MegaD."""

    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_has_entity_name = True
    _attr_release_url: str | None = RELEASE_URL
    _attr_supported_features = (UpdateEntityFeature.INSTALL
                                | UpdateEntityFeature.RELEASE_NOTES)

    def __init__(self, coordinator: MegaDCoordinator):
        super().__init__(coordinator)
        self._megad: MegaD = coordinator.megad
        self._lt_version_sw = self._megad.lt_version_sw
        self._attr_unique_id = f'{self._megad.id}-megad_firmware_update'
        self._attr_name = 'Обновление прошивки контроллера'
        self._current_version = self._megad.software
        self._latest_version = self._lt_version_sw.name
        self._attr_device_info = coordinator.devices_info()
        self.entity_id = f'update.{self._megad.id}-megad_firmware_update'

    @property
    def installed_version(self) -> str | None:
        """Version installed and in use."""
        return self._current_version

    @property
    def latest_version(self) -> str | None:
        """Latest version available for install."""
        return self._latest_version

    @cached_property
    def release_summary(self) -> str | None:
        """Summary of the release notes or changelog."""
        return self._lt_version_sw.short_descr

    @cached_property
    def title(self) -> str | None:
        """Title of the software.
        """
        return f'IP-адрес устройства: {self._megad.config.plc.ip_megad}'

    def release_notes(self) -> str | None:
        """Return full release notes."""
        return self._lt_version_sw.descr

    def version_is_newer(
            self, latest_version: str, installed_version: str) -> bool:
        """Return True if latest_version is newer than installed_version."""
        return bool(self._latest_version > self._current_version)

    @cached_property
    def release_url(self) -> str | None:
        """URL to the full release notes of the latest version available."""
        return self._attr_release_url

    def install(
            self, version: str | None, backup: bool = False, **kwargs: Any
    ) -> None:
        """Install an update."""
        self._attr_in_progress = True
        self._attr_update_percentage = 0
        megad_ip = self._megad.config.plc.ip_megad
        host_ip = asyncio.run_coroutine_threadsafe(
            async_get_source_ip(self.hass), self.hass.loop).result()
        _LOGGER.debug(f'Адрес хоста: {host_ip}, адрес MegaD: {megad_ip}')
        try:
            receive_socket = create_receive_socket(host_ip)
            receive_socket.settimeout(RECV_TIMEOUT)
            send_socket = create_send_socket()

            receive_socket.close()
            send_socket.close()
            self._attr_update_percentage = 100
            time.sleep(1)
        except (CreateSocketReceiveError, CreateSocketSendError):
            _LOGGER.error(f'Ошибка обновления ПО контроллера. Не удалось '
                          f'установить соединение с {megad_ip}')
        except Exception as e:
            _LOGGER.error(f'Ошибка обновления ПО контроллера. error: {e}')
            receive_socket.close()
            send_socket.close()
        finally:
            self._attr_in_progress = False
        # _LOGGER.info(f'имитация обновления прошивки!!!!!{version}')
        # time.sleep(5)
        # self._current_version = self._latest_version
