import asyncio
import logging
import os
import re
from datetime import datetime

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.translation import async_get_translations
from .const import DOMAIN, PATH_CONFIG_MEGAD
from .core.config_parser import async_read_configuration, write_config_megad
from .core.exceptions import InvalidIpAddress, WriteConfigError, \
    InvalidPassword

_LOGGER = logging.getLogger(__name__)


def validate_ip_address(ip: str) -> None:
    """Валидация ip адреса"""

    regex = re.compile(
        r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.)'
        r'{3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(:[0-9]{1,5})?$'
    )

    if not re.fullmatch(regex, ip):
        raise InvalidIpAddress


def validate_long_password(password: str) -> None:
    """Валидация длины пароля"""

    if len(password) > 3:
        raise InvalidPassword


class MegaDConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    data: dict = None

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input is not None:
            _LOGGER.debug(user_input)
            try:
                validate_ip_address(user_input['ip'])
                validate_long_password(user_input['password'])
                if not errors:
                    self.data = {
                        'url': f'http://{user_input["ip"]}/'
                               f'{user_input["password"]}/',
                        'ip': user_input['ip']
                    }
                return await self.async_step_get_config()
            except InvalidIpAddress:
                _LOGGER.error('Неверный формат ip адреса')
                errors['base'] = 'invalid_ip'
            except InvalidPassword:
                _LOGGER.error(f'Пароль длиннее 3х символов')
                errors['base'] = 'invalid_password'
            except Exception as e:
                _LOGGER.error(f'Что-то пошло не так, неизвестная ошибка. {e}')
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id='user',
            data_schema=vol.Schema(
                {
                    vol.Required(schema="ip", default='192.168.113.44'): str,
                    vol.Required(schema="password", default='sec'): str
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
            if user_input.get('config_menu') == 'select_config':
                return await self.async_step_select_config()
            if user_input.get('config_menu') == 'write_config':
                return await self.async_step_write_config()

        return self.async_show_form(
            step_id='get_config',
            data_schema=vol.Schema(
                {
                    vol.Required('config_menu'): vol.In({
                        'read_config': 'Прочитать конфигурацию с MegaD',
                        'select_config': 'Выбрать готовую конфигурацию',
                        'write_config': 'Записать конфигурацию на MegaD',
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

            await async_read_configuration(
                self.data['url'],
                user_input.get('name_file'),
                async_get_clientsession(self.hass)
            )
            return await self.async_step_select_config()

        return self.async_show_form(
            step_id='read_config',
            data_schema=vol.Schema(
                {
                    vol.Required(
                        schema="name_file",
                        default=f'ip{self.data["ip"].split(".")[-1]}_'
                                f'{datetime.now().strftime("%Y%m%d")}'
                    ): str
                }
            ),
            errors=errors
        )

    async def async_step_select_config(self, user_input=None):
        """Выбор конфигурации контроллера для создания сущности в НА"""
        errors: dict[str, str] = {}
        if user_input is not None:
            _LOGGER.debug(user_input)

        config_list = await asyncio.to_thread(os.listdir, PATH_CONFIG_MEGAD)
        config_list = [file for file in config_list if file != ".gitkeep"]

        return self.async_show_form(
            step_id='select_config',
            data_schema=vol.Schema(
                {
                    vol.Required('config_list'): vol.In(config_list)
                }
            ),
            errors=errors
        )

    async def async_step_write_config(self, user_input=None):
        """Выбор конфигурации контроллера для создания сущности в НА"""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                _LOGGER.debug(user_input)
                name_file = user_input.get('config_list')
                file_path = os.path.join(PATH_CONFIG_MEGAD, name_file)
                _LOGGER.debug(f'file_path: {file_path}')
                _LOGGER.debug(f'name_file: {name_file}')
                await write_config_megad(
                    str(file_path),
                    self.data['url'],
                    async_get_clientsession(self.hass)
                )
            except WriteConfigError as e:
                _LOGGER.error(f'Ошибка записи конфигурации в контроллер: {e}')
            except Exception as e:
                _LOGGER.error(f'Что-то пошло не так, неизвестная ошибка. {e}')

        config_list = await asyncio.to_thread(os.listdir, PATH_CONFIG_MEGAD)
        config_list = [file for file in config_list if file != ".gitkeep"]

        return self.async_show_form(
            step_id='write_config',
            data_schema=vol.Schema(
                {
                    vol.Required('config_list'): vol.In(config_list)
                }
            ),
            errors=errors
        )
