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
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from . import MegaDCoordinator
from .const import (
    RELEASE_URL, DOMAIN, ENTRIES, CURRENT_ENTITY_IDS, DEFAULT_IP, TIME_UPDATE
)
from .core.config_manager import MegaDConfigManager
from .core.const_fw import (
    RECV_TIMEOUT, BROADCAST_START, CHECK_DATA, BROADCAST_PORT
)
from .core.exceptions import (
    CreateSocketReceiveError, CreateSocketSendError, FWUpdateError
)
from .core.megad import MegaD
from .core.utils import (
    create_receive_socket, create_send_socket, turn_on_fw_update, download_fw,
    check_bootloader_version, get_broadcast_ip, reboot_megad, write_firmware,
    change_ip
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback
) -> None:
    entry_id = config_entry.entry_id
    coordinator = hass.data[DOMAIN][ENTRIES][entry_id]

    firmware_update_entity = MegaDFirmwareUpdate(coordinator, entry_id)
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

    def __init__(self, coordinator: MegaDCoordinator, entry_id):
        super().__init__(coordinator)
        self._megad: MegaD = coordinator.megad
        self._entry_id = entry_id
        self._lt_version_sw = self._megad.lt_version_sw
        self._attr_unique_id = f'{self._megad.id}-megad_firmware_update'
        self._attr_name = 'Обновление прошивки контроллера'
        self._current_version = self._megad.software
        self._latest_version = self._lt_version_sw.name
        self._attr_device_info = coordinator.devices_info()
        self.entity_id = f'update.{self._megad.id}-megad_firmware_update'
        self.progress = {'percentage': None}

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

    @property
    def update_percentage(self) -> int | float | None:
        """Update installation progress."""
        return self.progress['percentage']

    def install(
            self, version: str | None, backup: bool = False, **kwargs: Any
    ) -> None:
        """Install an update."""
        self.coordinator.update_interval = None
        receive_socket = None
        send_socket = None
        self._attr_in_progress = True
        self.progress['percentage'] = 0
        megad_ip = str(self._megad.config.plc.ip_megad)
        password = self._megad.config.plc.password
        host_ip = asyncio.run_coroutine_threadsafe(
            async_get_source_ip(self.hass), self.hass.loop).result()
        _LOGGER.debug(f'Адрес хоста: {host_ip}, адрес MegaD: {megad_ip}')
        try:
            file_path = download_fw(
                self._megad.lt_version_sw.link, self.progress
            )
            check_bootloader_version(megad_ip, password)
            self.progress['percentage'] = 11
            broadcast_ip = get_broadcast_ip(host_ip)
            broadcast_string = BROADCAST_START + CHECK_DATA

            receive_socket = create_receive_socket(host_ip)
            receive_socket.settimeout(RECV_TIMEOUT)
            send_socket = create_send_socket()
            self.progress['percentage'] = 12
            turn_on_fw_update(megad_ip, password)
            self.progress['percentage'] = 13

            for i in range(10):
                send_socket.sendto(
                    broadcast_string, (broadcast_ip, BROADCAST_PORT)
                )
                _LOGGER.debug(f'Попытка {i + 1}: Запрос отправлен контроллеру '
                              f'отправлен.')
                _LOGGER.debug(f'Попытка чтения ответа от MegaD')
                try:
                    receive_socket.settimeout(RECV_TIMEOUT)
                    pkt, peer = receive_socket.recvfrom(200)
                    _LOGGER.debug(f'Ответ получен от {peer}: {pkt}')
                    self.progress['percentage'] = 14
                    break
                except socket.timeout:
                    _LOGGER.debug('Таймаут при ожидании ответа.')

            receive_socket.settimeout(30)

            send_socket.sendto(
                broadcast_string, (broadcast_ip, BROADCAST_PORT)
            )
            _LOGGER.debug('Финальный запрос отправлен.')
            self.progress['percentage'] = 15

            try:
                pkt, peer = receive_socket.recvfrom(200)
                _LOGGER.debug(f'Финальный ответ получен от {peer}: {pkt}')
                self.progress['percentage'] = 16
            except socket.timeout:
                _LOGGER.warning('Таймаут при ожидании финального ответа.')
                raise Exception('Контроллер не отвечает.')

            if pkt[2] == 0x99 or pkt[2] == 0x9A:
                if pkt[2] == 0x99:
                    _LOGGER.warning('WARNING! Пожалуйста, обновите загрузчик!')
                    reboot_megad(send_socket, receive_socket, broadcast_ip)
                    raise Exception('Загрузчик устарел.')
                self.progress['percentage'] = 17
            else:
                _LOGGER.warning('Неподдерживаемый тип чипа atmega328!')
                raise Exception('Неподдерживаемый тип чипа atmega328!')

            firmware = b''
            with open(file_path, 'r') as fh:
                for line in fh:
                    if len(line) > 0 and line[8] == '0':
                        byte_count = line[1:3]
                        byte_count_int = int(byte_count, 16)
                        for i in range(byte_count_int):
                            pos = i * 2 + 9
                            byte_hex = line[pos:pos + 2]
                            byte = bytes.fromhex(byte_hex)
                            firmware += byte
            _LOGGER.debug(f'lenth_firmware: {len(firmware)}')
            self.progress['percentage'] = 18

            if len(firmware) > 258046:
                _LOGGER.warning(f'Размер прошивки слишком велик!')
                reboot_megad(send_socket, receive_socket, broadcast_ip)
                raise Exception('Слишком большой файл прошивки.')
            elif len(firmware) < 1000:
                _LOGGER.warning(f'Размер прошивки слишком мал!')
                reboot_megad(send_socket, receive_socket, broadcast_ip)
                raise Exception('Слишком маленький файл прошивки.')
            else:
                _LOGGER.debug('Файл прошивки прошёл проверку...')
                self.progress['percentage'] = 19

            write_firmware(
                send_socket,
                receive_socket,
                broadcast_ip,
                firmware,
                self.progress
            )

            reboot_megad(send_socket, receive_socket, broadcast_ip)

            receive_socket.close()
            receive_socket = None
            send_socket.close()
            send_socket = None
            self.progress['percentage'] = 83
            time.sleep(1)

            change_ip(DEFAULT_IP, megad_ip, password, broadcast_ip, host_ip)
            self.progress['percentage'] = 84

            self.progress['percentage'] = 85
            time.sleep(2) # тут если не ставить паузу то во время загрузки конфига прилетает что контроллер загружен
            asyncio.run_coroutine_threadsafe(
                self._write_config(), self.hass.loop
            )
            self.progress['percentage'] = 99
            time.sleep(1)

            # Надо понять как запустить асинхронную функцию в синхронной и поправить тут
            # Надо подумать над остановкой интеграции во время обновления контроллера. Возможно ввести какой-то флаг для этого
            # Подумать над процентовкой процесса обновления, пока она не отображается по неизвестной причине

            self.progress['percentage'] = 100
            self._current_version = self._latest_version
            time.sleep(1)
        except (CreateSocketReceiveError, CreateSocketSendError):
            _LOGGER.error(f'Ошибка обновления ПО контроллера. Не удалось '
                          f'установить соединение с {megad_ip}')
        except Exception as e:
            _LOGGER.error(f'Ошибка обновления ПО контроллера. error: {e}')
            _LOGGER.debug(f'Прогресс прошивки остановлен на '
                          f'{self.progress['percentage']}%')
            raise FWUpdateError('Произошла ошибка обновления ПО контроллера. '
                                'Если контроллер не запускается, то '
                                'воспользуйтесь режимом восстановления '
                                'https://ab-log.ru/smart-house/ethernet/megad-upgrade.')
        finally:
            self.coordinator.update_interval = TIME_UPDATE
            self._attr_in_progress = False
            if receive_socket:
                receive_socket.close()
            if send_socket:
                send_socket.close()
            _LOGGER.debug('Процесс прошивки завершён.')
            asyncio.run_coroutine_threadsafe(
                self.hass.config_entries.async_reload(self._entry_id),
                self.hass.loop
            )


    async def _write_config(self) -> None:
        """Записать конфиг на контроллер."""
        manager_config = MegaDConfigManager(
            self._megad.url,
            self._megad.config_path,
            async_get_clientsession(self.hass)
        )
        await manager_config.read_config_file()
        _LOGGER.debug(f'Прочитан файл конфигурации. Всего строк: '
                      f'{len(manager_config.settings)}')
        await manager_config.upload_config(timeout=0.2)
        _LOGGER.debug(f'Конфигурация загружена в контроллер.')