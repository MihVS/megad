import logging
from http import HTTPStatus

from aiohttp.web_request import Request
from aiohttp.web_response import Response

from homeassistant.components.http import HomeAssistantView
# from .. import MegaDCoordinator

from ..const import DOMAIN


_LOGGER = logging.getLogger(__name__)


class MegadHttpView(HomeAssistantView):
    """Класс представления HTTP для обработки запросов."""

    url = '/megad'
    name = 'megad'
    requires_auth = False

    async def get(self, request: Request):
        """Обрабатываем GET-запрос."""

        host = request.remote
        params: dict = dict(request.query)
        _LOGGER.debug(f'MegaD request4: {params}')
        hass = request.app['hass']
        entry_ids = hass.data[DOMAIN]
        id_megad = params.get('mdid')
        port_id = params.get('pt')
        coordinator = None
        for entry_id in entry_ids:
            coordinator_temp = hass.data[DOMAIN][entry_id]
            _LOGGER.info(f'coordinator: {coordinator_temp}')
            if coordinator_temp.megad.id == id_megad:
                coordinator = coordinator_temp

        # coordinator = next(
        #     (coordinator for coordinator in coordinators
        #      if coordinator.megad.id == id_megad),
        #     None
        # )
        if coordinator is None:
            _LOGGER.debug(f'Контроллер ip={host} не добавлен в НА')
            return Response(status=HTTPStatus.NOT_FOUND)

        if port_id is not None:
            coordinator.megad.update_port(port_id=port_id, data=params)
            # coordinator.async_set_updated_data(coordinator.megad)
