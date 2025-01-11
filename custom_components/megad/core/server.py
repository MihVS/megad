import logging

from aiohttp.web_request import Request

from homeassistant.components.http import HomeAssistantView

_LOGGER = logging.getLogger(__name__)


class MegadHttpView(HomeAssistantView):
    """Класс представления HTTP для обработки запросов."""

    url = '/megad'
    name = 'megad'
    requires_auth = False

    async def get(self, request: Request):
        """Обрабатываем GET-запрос."""

        _LOGGER.debug(f'MegaD request: {request.query_string}')
        # _LOGGER.debug(f'MegaD request4: {dict(request.query)}')
