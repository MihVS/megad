import logging
import re
from datetime import datetime

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN
from .core.config_parser import async_fetch_page, async_read_configuration
from .core.exceptions import InvalidIpAddress

_LOGGER = logging.getLogger(__name__)


def validate_ip_address(ip: str) -> None:
    """Валидация ip адреса"""

    regex = re.compile(
        r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.)'
        r'{3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(:[0-9]{1,5})?$'
    )

    if not re.fullmatch(regex, ip):
        raise InvalidIpAddress


class MegaDConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    data: dict = None

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input is not None:
            _LOGGER.debug(user_input)
            try:
                validate_ip_address(user_input['ip'])
                if not errors:
                    self.data = {
                        'url': f'http://{user_input["ip"]}/'
                               f'{user_input["password"]}/'
                    }
                return await self.async_step_get_config()
            except InvalidIpAddress:
                _LOGGER.error("Invalid IP address")
                errors['base'] = 'invalid_ip'

        return self.async_show_form(
            step_id='user',
            data_schema=vol.Schema(
                {
                    vol.Required(schema="ip", default='192.168.113.44'): str,
                    vol.Required(schema="password", default='sec'):
                        vol.All(str, vol.Length(max=3)),
                }
            ),
            errors=errors
        )

    async def async_step_get_config(self, user_input=None):
        """Главное меню выбора считывания конфигурации контроллера"""
        errors: dict[str, str] = {}
        if user_input is not None:
            _LOGGER.debug(user_input)
            if user_input.get('config_menu') == 'read_config':
                return await self.async_step_read_config()

        return self.async_show_form(
            step_id='get_config',
            data_schema=vol.Schema(
                {
                    vol.Required('config_menu'): vol.In({
                        'read_config': 'Read config',
                        'select_config': 'Select config',
                        'write_config': 'Write config',
                    })
                }
            ),
            errors=errors
        )

    async def async_step_read_config(self, user_input=None):
        """Считывание конфигурации контроллера"""
        errors: dict[str, str] = {}
        if user_input is not None:
            _LOGGER.debug(user_input)
            _LOGGER.debug(user_input.get('name_file'))
            # page = await async_fetch_page(
            #     self.data['url'], async_get_clientsession(self.hass))
            await async_read_configuration(
                self.data['url'],
                user_input.get('name_file'),
                async_get_clientsession(self.hass)
            )
            # _LOGGER.debug(page)

        return self.async_show_form(
            step_id='read_config',
            data_schema=vol.Schema(
                {
                    vol.Required(
                        schema="name_file",
                        default=f'config_{datetime.now().strftime("%Y_%m_%d")}'
                    ): str
                }
            ),
            errors=errors
        )
