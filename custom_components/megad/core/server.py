import logging
from http import HTTPStatus

from aiohttp.web_request import Request
from aiohttp.web_response import Response

from homeassistant.components.http import HomeAssistantView
from .const_parse import EXTRA
from ..const import DOMAIN, ENTRIES, MEGAD_ID, MEGAD_STATE, PORT_ID

_LOGGER = logging.getLogger(__name__)


class MegadHttpView(HomeAssistantView):
    """Класс представления HTTP для обработки запросов."""

    url = '/megad'
    name = 'megad'
    requires_auth = False

    @staticmethod
    async def restore_after_reboot(coordinator):
        """Восстановление состояния контроллера после перезагрузки"""
        await coordinator.restore_status_ports()
        await coordinator.megad.set_current_time()

    async def get(self, request: Request):
        """Обрабатываем GET-запрос."""
        host = request.remote
        params: dict = dict(request.query)
        _LOGGER.debug(f'MegaD request: {params}')
        hass = request.app['hass']
        if hass.data.get(DOMAIN) is None:
            _LOGGER.info(f'Интеграция загружается, запрос не обработан: '
                         f'{params}')
            return Response(status=HTTPStatus.NOT_FOUND)
        entry_ids = hass.data[DOMAIN][ENTRIES]
        id_megad = params.get(MEGAD_ID)
        state_megad = params.get(MEGAD_STATE)
        ext = any(EXTRA in key for key in params)
        port_id = params.get(PORT_ID)
        coordinator = None
        for entry_id in entry_ids:
            coordinator_temp = hass.data[DOMAIN][ENTRIES][entry_id]
            try:
                if coordinator_temp.megad.domain == host:
                    coordinator = coordinator_temp
            except AttributeError:
                _LOGGER.warning(
                    f'coordinator_temp type {type(coordinator_temp)}. '
                    f'params: {params}'
                )

        if coordinator is None:
            _LOGGER.debug(f'Контроллер ip={host} не добавлен в НА')
            return Response(status=HTTPStatus.NOT_FOUND)

        if coordinator.megad.is_flashing:
            _LOGGER.debug(f'Контроллер ip={host} в процессе обновления.')
            return None

        if state_megad == '1':
            _LOGGER.info(f'megad-{id_megad} был перезагружен')
            hass.async_create_task(self.restore_after_reboot(coordinator))

        if port_id is not None:
            await coordinator.update_port_state(
                port_id=port_id, data=params, ext=ext
            )
        return Response(status=HTTPStatus.OK)
