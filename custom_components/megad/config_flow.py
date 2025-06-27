import asyncio
import logging
import os
import re
from datetime import datetime
from http import HTTPStatus
from urllib.parse import urlparse

import aiohttp
import voluptuous as vol
from pydantic import ValidationError

from homeassistant import config_entries
from homeassistant.components.network import async_get_source_ip
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import selector
from .const import (
    DOMAIN, PATH_CONFIG_MEGAD, DEFAULT_IP, DEFAULT_PASSWORD, ENTRIES
)
from .core.config_manager import MegaDConfigManager
from .core.config_parser import (
    async_get_page_config, get_slug_server
)
from .core.const_fw import DEFAULT_IP_LIST
from .core.exceptions import (
    WriteConfigError, InvalidPassword, InvalidAuthorized, InvalidSlug,
    InvalidIpAddressExist, NotAvailableURL, SearchMegaDError, InvalidIpAddress,
    InvalidPasswordMegad, ChangeIPMegaDError, InvalidMegaDID
)
from .core.utils import (
    get_list_config_megad, get_broadcast_ip, get_megad_ip, change_ip
)

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


def validate_ip_address(ip: str) -> None:
    """Валидация ip адреса"""
    regex = re.compile(
        r'^((25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\.)'
        r'{3}(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])$'
    )
    if not re.fullmatch(regex, ip):
        raise InvalidIpAddress


def validate_long_password(password: str) -> None:
    """Валидация длины пароля"""
    if len(password) > 5:
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


async def validate_megad_id(megad_id) -> None:
    """Валидация поля id контроллера. Должно быть непустым."""
    if megad_id == '':
        raise InvalidMegaDID


class MegaDBaseFlow(config_entries.ConfigEntryBaseFlow):
    """Базовый класс для ConfigFlow и OptionsFlow."""

    data = {}

    def get_path_to_config(self, name_config='') -> str:
        """Возвращает путь до каталога с настройками контроллера"""
        configs_path = self.hass.config.path(PATH_CONFIG_MEGAD)
        os.makedirs(configs_path, exist_ok=True)
        path = os.path.join(configs_path, name_config)
        return str(path)

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
                url = self.data.get('url')
                session = async_get_clientsession(self.hass)
                await validate_slug(url, session)
                name_file = user_input.get('config_list')
                file_path = self.get_path_to_config(name_file)
                self.data['file_path'] = file_path
                self.data['name_file'] = name_file
                _LOGGER.debug(f'file_path: {file_path}')
                _LOGGER.debug(f'name_file: {name_file}')
                manager_config = MegaDConfigManager(url, file_path, session)
                await manager_config.read_config_file(file_path)
                await validate_megad_id(manager_config.get_mega_id())
                megad_config = await manager_config.create_config_megad()
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
            except InvalidMegaDID:
                _LOGGER.error(f'Проверьте в настройках контроллера поле '
                              f'Megad-ID. Оно должно быть непустым.')
                errors["base"] = "validate_megad_id"
            except InvalidSlug:
                _LOGGER.error(f'Проверьте в настройках контроллера поле '
                              f'Script. Оно должно быть = megad.')
                errors['base'] = 'validate_slug'
            except ValidationError as e:
                field_server = False
                for error in e.errors():
                    if error['loc'][0] == 'srvt':
                        field_server = True
                if field_server:
                    _LOGGER.error(f'Проверьте в настройках контроллера '
                                  f'поле SRV. Адрес сервера должен быть '
                                  f'указан.')
                    errors['base'] = 'field_server_empty'
                else:
                    _LOGGER.error(f'Ошибка валидации файла конфигурации: {e}')
                    errors['base'] = 'validate_config'
            except aiohttp.client_exceptions.ClientResponseError as e:
                _LOGGER.error(f'Ошибка авторизации MegaD: {e}')
                errors['base'] = 'unauthorized'
            except Exception as e:
                _LOGGER.error(f'Что-то пошло не так, неизвестная ошибка. {e}')
                errors['base'] = "unknown"

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
                name_file = user_input.get('name_file')
                config_path = self.get_path_to_config(name_file)
                config_manager = MegaDConfigManager(
                    self.data['url'],
                    config_path,
                    async_get_clientsession(self.hass)
                )
                await config_manager.read_config()
                await config_manager.save_config_to_file()
                self.data['name_file'] = name_file
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
                config_path = self.get_path_to_config(name_file)
                _LOGGER.debug(f'file_path: {config_path}')
                _LOGGER.debug(f'name_file: {name_file}')
                config_manager = MegaDConfigManager(
                    self.data['url'],
                    config_path,
                    async_get_clientsession(self.hass)
                )
                await config_manager.read_config_file(config_path)
                await config_manager.upload_config(timeout=0.2)
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
        """Стартовое меню"""
        errors: dict[str, str] = {}
        language = self.hass.config.language
        options_ru = {
            'add_device': 'Добавить новое устройство',
            'change_ip': 'Найти устройство и изменить IP-адрес'
        }
        options_en = {
            'Добавить новое устройство': 'add_device',
            'Найти устройство и изменить IP-адрес': 'change_ip'
        }
        if language == 'ru':
            options = [name for name in options_ru.values()]
        else:
            options = [name for name in options_ru]
        if user_input is not None:
            if language == 'ru':
                value_ru = user_input.get('selection')
                user_input.update({'selection': options_en[value_ru]})
            _LOGGER.debug(f'step_user {user_input}')
            try:
                if user_input.get('selection') == 'add_device':
                    return await self.async_step_start()
                if user_input.get('selection') == 'change_ip':
                    return await self.async_step_change_ip_device()
            except Exception as e:
                _LOGGER.error(f'Что-то пошло не так, неизвестная ошибка. {e}')
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id='user',
            data_schema=vol.Schema({
                vol.Required('selection'): selector({
                    'select': {
                        'options': options,
                        'mode': 'list'
                    }
                })
            }),
            errors=errors
        )

    async def scan_device(self) -> list[str]:
        """Возвращает список адресов устройств."""
        ip_addr = await async_get_source_ip(self.hass)
        _LOGGER.debug(f'ip address of host: {ip_addr}')
        broadcast_ip = get_broadcast_ip(ip_addr)
        _LOGGER.debug(f'broadcast ip address: {broadcast_ip}')
        return await asyncio.to_thread(get_megad_ip, ip_addr, broadcast_ip)

    async def change_ip_device(self, old_ip, new_ip, password):
        """Изменяет ip устройства."""
        ip_addr = await async_get_source_ip(self.hass)
        broadcast_ip = get_broadcast_ip(ip_addr)
        await asyncio.to_thread(
            change_ip, old_ip, new_ip, password, broadcast_ip, ip_addr
        )

    async def async_step_change_ip_device(self, user_input=None):
        """Меню изменения ip адреса устройства"""
        _LOGGER.debug(f'step_change_ip_device: {user_input}')
        errors: dict[str, str] = {}
        ip_devices = self.data.get('ip_devices', DEFAULT_IP_LIST)
        try:
            if user_input is not None:
                _LOGGER.debug(f'step_change_ip_device: {user_input}')
                if user_input.get('return_main_menu', False):
                    return await self.async_step_user()

                old_ip = user_input.get('old_ip')
                new_ip = user_input.get('new_ip')
                password = user_input.get('password')
                validate_ip_address(old_ip)
                validate_ip_address(new_ip)
                validate_long_password(password)
                _LOGGER.info(f'Пробую изменить IP-адрес {old_ip} на {new_ip}')
                await self.change_ip_device(old_ip, new_ip, password)
                return await self.async_step_user()
            else:
                ip_devices = await self.scan_device()
                self.data['ip_devices'] = ip_devices
        except SearchMegaDError:
            errors['base'] = 'search_error'
        except ChangeIPMegaDError:
            _LOGGER.warning(f'Ошибка изменения адреса {old_ip} на {new_ip}')
            errors['base'] = 'invalid_change_ip'
        except InvalidPasswordMegad:
            _LOGGER.warning('Неверный пароль для MegaD!')
            errors['base'] = 'unauthorized'
        except InvalidPassword:
            _LOGGER.warning(f'Пароль длиннее 5 символов: {password}')
            errors['base'] = 'invalid_password'
        except InvalidIpAddress:
            _LOGGER.warning(f'Проверьте ip адрес: {old_ip}, {new_ip}')
            errors['base'] = 'invalid_ip'
        except Exception as e:
            _LOGGER.error(f'Что-то пошло не так, неизвестная ошибка. {e}')
            errors['base'] = 'unknown'

        return self.async_show_form(
            step_id='change_ip_device',
            data_schema=vol.Schema(
            {
                vol.Required('old_ip'): vol.In(ip_devices),
                vol.Required(schema="password", default=self.data.get(
                    'password', DEFAULT_PASSWORD
                )): str,
                vol.Required(schema='new_ip', default=DEFAULT_IP): str,
                vol.Optional(schema="return_main_menu"): bool
            }
            ),
            errors=errors
        )

    async def async_step_start(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input is not None:
            _LOGGER.debug(f'step_user: {user_input}')
            if user_input.get('change_ip_device', False):
                return await self.async_step_change_ip_device()
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
                _LOGGER.error(f'Пароль длиннее 5 символов: {password}')
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
            step_id='start',
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
