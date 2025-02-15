import asyncio
import logging
import os
from datetime import datetime
from http import HTTPStatus
from urllib.parse import urlparse

import aiohttp
import voluptuous as vol
from pydantic import ValidationError

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import (
    DOMAIN, PATH_CONFIG_MEGAD, DEFAULT_IP, DEFAULT_PASSWORD, ENTRIES
)
from .core.config_parser import (
    async_read_configuration, write_config_megad, async_get_page_config,
    get_slug_server, create_config_megad
)
from .core.exceptions import (WriteConfigError,
                              InvalidPassword, InvalidAuthorized, InvalidSlug,
                              InvalidIpAddressExist, NotAvailableURL)
from .core.utils import get_list_config_megad

_LOGGER = logging.getLogger(__name__)


async def validate_url(hass: HomeAssistant, user_input: str) -> str:
    """Проверка доступности url"""
    session = async_get_clientsession(hass)
    _LOGGER.debug(f'Полученный URL: {user_input}')
    if not user_input.startswith(('http://', 'https://')):
        user_input = f'https://{user_input}'

    parsed_url = urlparse(user_input)
    base_url = f'{parsed_url.scheme}://{parsed_url.netloc}'

    if parsed_url.scheme == 'http':
        urls = [base_url]
    else:
        urls = [base_url, base_url.replace('https://', 'http://')]

    for url in urls:
        try:
            async with session.get(url, timeout=3) as response:
                if response.status == 200:
                    _LOGGER.debug(f'Преобразованный URL: {url}')
                    return url
        except Exception as err:
            _LOGGER.info(f'Не удалось соединиться с URL: {url}. Ошибка: {err}')
            continue

    raise NotAvailableURL(f'Контроллер недоступен по {urls}')


def check_exist_ip(ip: str, hass_data: dict) -> None:
    """Проверка занятости ip адреса другими контроллерами"""
    for entity_id, controller in hass_data.items():
        if str(controller.megad.config.plc.ip_megad) == ip:
            raise InvalidIpAddressExist


def validate_long_password(password: str) -> None:
    """Валидация длины пароля"""
    if len(password) > 3:
        raise InvalidPassword


async def validate_password(url: str, session: aiohttp.ClientSession) -> None:
    """Валидация пароля"""
    async with session.get(url) as response:
        code = response.status
        if code == HTTPStatus.UNAUTHORIZED:
            raise InvalidAuthorized


async def validate_slug(url: str, session: aiohttp.ClientSession) -> None:
    """Валидация поля script в контроллере. Должно быть = megad."""
    page = await async_get_page_config(1, url, session)
    slug = await get_slug_server(page)
    if slug != DOMAIN:
        raise InvalidSlug


class MegaDBaseFlow(config_entries.ConfigEntryBaseFlow):
    """Базовый класс для ConfigFlow и OptionsFlow."""

    data = {}

    def get_path_to_config(self) -> str:
        """Возвращает путь до каталога с настройками контроллера"""
        config_path = self.hass.config.path(PATH_CONFIG_MEGAD)
        os.makedirs(config_path, exist_ok=True)
        return config_path

    def data_schema_main(self):
        return vol.Schema(
                {
                    vol.Required(
                        schema='ip', default=self.data.get(
                            'ip', DEFAULT_IP
                        )): str,
                    vol.Required(schema="password", default=self.data.get(
                        'password', DEFAULT_PASSWORD
                        )): str
                }
            )

    def data_schema_read_config(self):
        return vol.Schema(
                {
                    vol.Required(
                        schema="name_file",
                        default=f'ip{self.data["ip"].split(".")[-1]}_'
                                f'{datetime.now().strftime("%Y%m%d")}.cfg'
                    ): str,
                    vol.Optional(schema="return_main_menu"): bool
                }
        )

    async def validate_user_input_step_main(
            self, base_url: str, password: str) -> None:
        url = f'{base_url}/{password}/'
        validate_long_password(password)
        await validate_password(
            url, async_get_clientsession(self.hass)
        )

    async def async_step_get_config(self, user_input=None):
        """Главное меню выбора считывания конфигурации контроллера"""
        errors: dict[str, str] = {}
        if user_input is not None:
            _LOGGER.debug(f'step_get_config: {user_input}')
            if user_input.get('config_menu') == 'read_config':
                return await self.async_step_read_config()
            if user_input.get('config_menu') == 'select_config':
                return await self.async_step_select_config()
            if user_input.get('config_menu') == 'write_config':
                return await self.async_step_write_config()

        menu = {
            'read_config': 'Прочитать конфигурацию с MegaD',
            'select_config': 'Выбрать готовую конфигурацию',
            'write_config': 'Записать конфигурацию на MegaD'
        }
        config_list = await get_list_config_megad(
            path=self.get_path_to_config()
        )
        if not config_list:
            menu = {'read_config': 'Прочитать конфигурацию с MegaD'}

        return self.async_show_form(
            step_id='get_config',
            data_schema=vol.Schema(
                {
                    vol.Required('config_menu'): vol.In(menu)
                }
            ),
            errors=errors
        )

    async def async_step_select_config(self, user_input=None):
        """Выбор конфигурации контроллера для создания сущности в НА"""
        errors: dict[str, str] = {}
        name_file = self.data.get('name_file', '')
        if user_input is not None:
            _LOGGER.debug(f'step_select_config {user_input}')
            if user_input.get('return_main_menu', False):
                return await self.async_step_get_config()
            try:
                await validate_slug(
                    self.data.get('url'),
                    async_get_clientsession(self.hass)
                )
                name_file = user_input.get('config_list')
                file_path = str(os.path.join(
                    self.get_path_to_config(), name_file)
                )
                self.data['file_path'] = file_path
                self.data['name_file'] = name_file
                _LOGGER.debug(f'file_path: {file_path}')
                _LOGGER.debug(f'name_file: {name_file}')
                megad_config = await create_config_megad(file_path)
                json_data = megad_config.model_dump_json(indent=2)
                _LOGGER.debug(f'megad_config_json: \n{json_data}')
                if self.data.get('options'):
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=self.data
                    )
                    return self.async_create_entry(
                        title=megad_config.plc.megad_id,
                        data=self.data
                    )
                else:
                    return self.async_create_entry(
                        title=megad_config.plc.megad_id,
                        data=self.data
                    )
            except InvalidSlug:
                _LOGGER.error(f'Проверьте в настройках контроллера поле '
                              f'Script. Оно должно быть = megad.')
                errors["base"] = "validate_slug"
            except ValidationError as e:
                _LOGGER.error(f'Ошибка валидации файла конфигурации: {e}')
                errors["base"] = "validate_config"
            except Exception as e:
                _LOGGER.error(f'Что-то пошло не так, неизвестная ошибка. {e}')
                errors["base"] = "unknown"

        config_list = await get_list_config_megad(
            name_file, self.get_path_to_config()
        )

        return self.async_show_form(
            step_id='select_config',
            data_schema=vol.Schema(
                {
                    vol.Required('config_list'): vol.In(config_list),
                    vol.Optional(schema="return_main_menu"): bool
                }
            ),
            errors=errors
        )

    async def async_step_read_config(self, user_input=None):
        """Считывание конфигурации контроллера"""
        errors: dict[str, str] = {}
        if user_input is not None:
            _LOGGER.debug(f'step_read_config: {user_input}')
            if user_input.get('return_main_menu', False):
                return await self.async_step_get_config()
            try:
                await async_read_configuration(
                    self.data['url'],
                    user_input.get('name_file'),
                    async_get_clientsession(self.hass),
                    self.get_path_to_config()
                )
                self.data['name_file'] = user_input.get('name_file')
                return await self.async_step_select_config()
            except aiohttp.ClientError as e:
                _LOGGER.error(f'Ошибка запроса к контроллеру '
                              f'при чтении конфигурации {e}')
                errors['base'] = 'read_config_error'
            except Exception as e:
                _LOGGER.error(f'Что-то пошло не так, неизвестная ошибка. {e}')
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id='read_config',
            data_schema=self.data_schema_read_config(),
            errors=errors
        )

    async def async_step_write_config(self, user_input=None):
        """Выбор конфигурации контроллера для записи в него"""
        errors: dict[str, str] = {}
        name_file = self.data.get('name_file', '')

        if user_input is not None:
            _LOGGER.debug(f'step_write_config: {user_input}')
            if user_input.get('return_main_menu', False):
                return await self.async_step_get_config()
            try:
                name_file = user_input.get('config_list')
                file_path = os.path.join(self.get_path_to_config(), name_file)
                _LOGGER.debug(f'file_path: {file_path}')
                _LOGGER.debug(f'name_file: {name_file}')
                await write_config_megad(
                    str(file_path),
                    self.data['url'],
                    async_get_clientsession(self.hass)
                )
                return await self.async_step_get_config()
            except WriteConfigError as e:
                _LOGGER.error(f'Ошибка записи конфигурации в контроллер: {e}')
            except Exception as e:
                _LOGGER.error(f'Что-то пошло не так, неизвестная ошибка. {e}')

        config_list = await get_list_config_megad(
            name_file, self.get_path_to_config()
        )
        return self.async_show_form(
            step_id='write_config',
            data_schema=vol.Schema(
                {
                    vol.Required('config_list'): vol.In(config_list),
                    vol.Optional(schema="return_main_menu"): bool
                }
            ),
            errors=errors
        )


class MegaDConfigFlow(MegaDBaseFlow, config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Create the options flow."""
        return OptionsFlowHandler()

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input is not None:
            _LOGGER.debug(f'step_user: {user_input}')
            ip = user_input['ip']
            password = user_input['password']
            try:
                base_url = await validate_url(self.hass, ip)
                url = f'{base_url}/{user_input["password"]}/'
                await self.validate_user_input_step_main(base_url, password)
                if DOMAIN in self.hass.data:
                    check_exist_ip(ip, self.hass.data[DOMAIN][ENTRIES])
                if not errors:
                    self.data = {
                        'url': url,
                        'ip': user_input['ip'],
                        'password': password
                    }
                return await self.async_step_get_config()
            except InvalidIpAddressExist:
                _LOGGER.error(f'IP адрес уже используется в интеграции: {ip}')
                errors['base'] = 'ip_exist'
            except NotAvailableURL:
                _LOGGER.error(f'Адрес не доступен: {ip}')
                errors['base'] = 'not_available_url'
            except InvalidPassword:
                _LOGGER.error(f'Пароль длиннее 3х символов: {password}')
                errors['base'] = 'invalid_password'
            except InvalidAuthorized:
                _LOGGER.error(f'Вы ввели неверный пароль: {password}')
                errors['base'] = 'unauthorized'
            except (aiohttp.client_exceptions.ClientConnectorError,
                    asyncio.TimeoutError) as e:
                _LOGGER.error(f'Контроллер недоступен. Проверьте ip адрес: '
                              f'{ip}. {e}')
                errors['base'] = 'megad_not_available'
            except Exception as e:
                _LOGGER.error(f'Что-то пошло не так, неизвестная ошибка. {e}')
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id='user',
            data_schema=self.data_schema_main(),
            errors=errors
        )


class OptionsFlowHandler(MegaDBaseFlow, config_entries.OptionsFlow):

    async def async_step_init(self, user_input):
        """Manage the options."""
        errors: dict[str, str] = {}
        self.data = dict(self.config_entry.data)
        self.data['options'] = True

        if user_input is not None:
            _LOGGER.debug(f'step_init: {user_input}')
            ip = user_input['ip']
            password = user_input['password']
            try:
                base_url = await validate_url(self.hass, ip)
                url = f'{base_url}/{user_input["password"]}/'
                await self.validate_user_input_step_main(base_url, password)
                if not errors:
                    self.data.update(user_input)
                    self.data.update({'url': url})
                return await self.async_step_get_config()
            except NotAvailableURL:
                _LOGGER.error(f'Адрес не доступен: {ip}')
                errors['base'] = 'not_available_url'
            except InvalidPassword:
                _LOGGER.error(f'Пароль длиннее 3х символов: {password}')
                errors['base'] = 'invalid_password'
            except InvalidAuthorized:
                _LOGGER.error(f'Вы ввели неверный пароль: {password}')
                errors['base'] = 'unauthorized'
            except (aiohttp.client_exceptions.ClientConnectorError,
                    asyncio.TimeoutError) as e:
                _LOGGER.error(f'Контроллер недоступен. Проверьте ip адрес: '
                              f'{ip}. {e}')
                errors['base'] = 'megad_not_available'
            except Exception as e:
                _LOGGER.error(f'Что-то пошло не так, неизвестная ошибка. {e}')
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id='init',
            data_schema=self.data_schema_main(),
            errors=errors
        )
