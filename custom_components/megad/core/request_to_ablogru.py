import logging
from datetime import datetime, timedelta
from http import HTTPStatus

import async_timeout

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .. import TIME_OUT_UPDATE_DATA
from ..const import RELEASE_URL, DOMAIN, ENTRIES

_LOGGER = logging.getLogger(__name__)


class FirmwareChecker:
    """Класс для проверки последней версии прошивки MegaD."""

    def __init__(self, hass):
        self.hass = hass
        self.session = async_get_clientsession(hass)
        self.entry_id = next(iter(hass.data[DOMAIN][ENTRIES]), 'default id')
        self.headers = {
            'User-Agent': f'Home Assistant MegaD-2561: {self.entry_id}',
            'Accept': 'text/html'
        }
        self.page_firmware = None
        self._last_check = None

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
                    url=RELEASE_URL, headers=self.headers
                )
                if response.status == HTTPStatus.OK:
                    self.page_firmware = await response.text()
                else:
                    raise Exception(f'Статус запроса: {response.status}')
        except Exception as e:
            _LOGGER.warning(f'Неудачная попытка проверки последней доступной '
                            f'версии прошивки. Ошибка: {e}')
