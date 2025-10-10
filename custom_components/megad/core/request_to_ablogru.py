import logging
import random
from datetime import datetime, timedelta
from http import HTTPStatus

import async_timeout

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const_fw import BROWSER_UA
from ..const import RELEASE_URL, DOMAIN, ENTRIES, TIME_OUT_UPDATE_DATA

_LOGGER = logging.getLogger(__name__)


class FirmwareChecker:
    """Класс для проверки последней версии прошивки MegaD."""

    def __init__(self, hass):
        self.hass = hass
        self.session = async_get_clientsession(hass)
        self.entry_id = next(iter(hass.data[DOMAIN][ENTRIES]), 'default id')
        self.page_firmware = None
        self._last_check = None

    def _get_headers(self) -> dict:
        """Формирует заголовки."""
        ua = f'{random.choice(BROWSER_UA)} Build/{self.entry_id}'
        headers = {
            "User-Agent": ua,
            "Accept-Language": "ru-RU,ru;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        return headers

    async def update_page_firmwares(self):
        """Обновить страницу с доступными прошивками."""
        try:
            if self._last_check is None:
                self._last_check = datetime.now()
                _LOGGER.debug('Обновлено время последней проверки прошивки.')
            elif datetime.now() - self._last_check < timedelta(hours=12):
                return
            else:
                _LOGGER.debug('Обновлено время последней проверки прошивки.')
                self._last_check = datetime.now()
            async with async_timeout.timeout(TIME_OUT_UPDATE_DATA):
                _LOGGER.debug(f'Запрос страницы прошивки для MegaD url: '
                              f'{RELEASE_URL}')
                response = await self.session.get(
                    url=RELEASE_URL, headers=self._get_headers()
                )
                if response.status == HTTPStatus.OK:
                    self.page_firmware = await response.text()
                    if not self.page_firmware:
                        _LOGGER.warning(f'Страница запроса прошивки пустая. '
                                        f'Последняя версия не установлена.')
                else:
                    raise Exception(f'Статус запроса: {response.status}')
        except Exception as e:
            _LOGGER.warning(f'Неудачная попытка проверки последней доступной '
                            f'версии прошивки. Ошибка: {e}')
