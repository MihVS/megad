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

        params: dict = dict(request.query)
        _LOGGER.debug(f'MegaD request4: {params}')
        id_megad = params.get('mdid')
        port = params.get('pt')
