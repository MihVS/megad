import asyncio
import logging
import re
from urllib.parse import parse_qsl

import aiofiles
import aiohttp
import async_timeout
from aiohttp import ClientResponse
from bs4 import BeautifulSoup

from .const_parse import *
from .exceptions import WriteConfigError
from .models_megad import (
    DeviceMegaD, PortConfig, PortInConfig, PortOutRelayConfig,
    PortOutPWMConfig, OneWireSensorConfig, IButtonConfig, WiegandD0Config,
    WiegandConfig, DHTSensorConfig, PortSensorConfig, I2CSDAConfig, I2CConfig,
    AnalogPortConfig, SystemConfigMegaD, PIDConfig
)

_LOGGER = logging.getLogger(__name__)


class MegaDConfigManager:
    """Класс для парсинга и обработки конфигурации контроллера"""

    def __init__(
            self, url: str,
            config_file_path: str,
            session: aiohttp.ClientSession,
    ):
        self.url = url
        self.config_file_path = config_file_path
        self.session = session
        self.settings = []
        self.len_main_settings = 0

    async def request_to_megad(self, params: dict | str) -> ClientResponse:
        """Отправка запроса к контроллеру"""
        async with async_timeout.timeout(TIME_OUT_UPDATE):
            if isinstance(params, str):
                response = await self.session.get(url=f'{self.url}?{params}')
            else:
                response = await self.session.get(url=self.url, params=params)
        return response

    async def fetch_page(self, params: dict) -> str:
        """Получает страницу конфигурации контроллера."""
        _LOGGER.debug(f'Запрос конфигурации контроллера MegaD. '
                      f'URL: {self.url}, params: {params}')
        response = await self.request_to_megad(params)
        page = await response.text(encoding='cp1251')
        return page

    async def get_base_params(self) -> list[dict]:
        """Получает список параметров для базовых запросов конфигурации"""
        page_params = [
            {CONFIG: MAIN_CONFIG}, {CONFIG: ID_CONFIG}, {CONFIG: TIME_CONFIG},
            {CONFIG: KEY_CONFIG}
        ]
        first_page = await self.fetch_page(params={})
        if first_page and "IN/OUT" in first_page:
            ports = 45 if "[44," in first_page else 37
        else:
            ports_match = re.findall(r'/sec/\?pt=(\d+)', first_page or "")
            if ports_match:
                ports = max(
                    map(int, ports_match))
            else:
                ports = 0
        page_params.extend({PORT: i} for i in range(ports + 1))
        page_params.extend(
            {CONFIG: CONDITION_CONFIG, CONDITION: i} for i in range(10)
        )
        page_params.extend({CONFIG: PID_CONFIG, PID: i} for i in range(5))
        page_params.extend(
            {CONFIG: SCREEN_CONFIG, SECTION: i} for i in range(5)
        )
        page_params.extend(
            {CONFIG: SCREEN_CONFIG, ELEMENT: i} for i in range(16)
        )
        return page_params

    @staticmethod
    def get_params(page: str) -> str:
        """Получает параметры настройки страницы контроллера"""
        params = ''
        soup = BeautifulSoup(page, 'lxml')
        for form in soup.find_all('form'):
            if form.get('style') == 'display:inline':
                continue
            for inp in form.find_all('input'):
                if inp.get('type') != "submit":
                    name = inp.get('name')
                    value = inp.get('value', '')
                    if inp.get('type') == "checkbox":
                        value = 'on' if inp.has_attr('checked') else ''
                    params += f"{name}={value}&"

        for select in soup.find_all('select'):
            name = select.get('name')
            selected_option = select.find('option', selected=True)
            if selected_option:
                value = selected_option.get('value', '')
                params += f"{name}={value}&"
        return params.rstrip('&')

    @staticmethod
    def decode_title(input_string: str) -> str:
        """Преобразует поле title в правильную кодировку для Русского языка"""
        if '&emt' in input_string:
            title = 'emt'
        elif '&pidt' in input_string:
            title = 'pidt'
        else:
            title = ''
        if title:
            query_params = dict(parse_qsl(
                input_string, keep_blank_values=True)
            )
            title_value = query_params[title]
            title_value_cp1251 = title_value.encode('cp1251')
            title_value_urlencoded = ''.join(
                f'%{hex(b)[2:].upper()}' if (b > 127) or (b in b' #%&+?/'
                  ) else chr(b) for b in title_value_cp1251
            )
            query_params[title] = title_value_urlencoded
            output_string = ''

            for key, value in query_params.items():
                output_string += f'{key}={value}&'
            return output_string[:-1]
        else:
            return input_string

    @staticmethod
    def _check_url(url: str, check: bool) -> bool:
        """Проверяет url на необходимость добавления параметра nr=1"""
        if check:
            return True
        return True if "cf=1&" in url else False

    @staticmethod
    def _check_extend_port(setting_line) -> int |  None:
        """Проверяет наличие подключенного расширения I2C к порту."""
        params = dict(
            parse_qsl(setting_line, keep_blank_values=True, encoding='cp1251')
        )
        type_port = params.get(TYPE_PORT)
        type_device = params.get(TYPE_DEVICE)
        if type_port == I2C and type_device in (PCA9685, MCP230XX):
            return int(params.get(PORT_NUMBER))

    async def process_page(self, params, check: bool) -> str:
        """Получает url настроек для файла конфигурации."""
        page_content = await self.fetch_page(params)
        if not page_content:
            return ''
        conf_url = self.get_params(page_content)
        if conf_url and conf_url != 'cf=<br':
            if not self._check_url(conf_url, check):
                conf_url = conf_url + '&nr=1'
                conf_url = self.decode_title(conf_url)
            return conf_url + '\n'
        return ''

    async def add_extra_config(self, extended_ports: list):
        """Добавляет порты расширителей к настройкам конфигурации"""
        count_ports = len(extended_ports)
        i = 1
        for port_id in extended_ports:
            j = 0
            for extra_port_id in range(16):
                params = {PORT: port_id, EXTRA: extra_port_id}
                check = False
                if i == count_ports and j == 15:
                    check = True
                j += 1
                setting_line = await self.process_page(params, check)
                if setting_line:
                    self.settings.append(setting_line)
            i += 1

    async def read_config(self):
        """Чтение конфигурации с контроллера"""
        extended_ports: list[int] = []
        page_params = await self.get_base_params()
        count_line = len(page_params)
        i = 1
        for page_param in page_params:
            check = False
            if i == count_line:
                check = True
            i += 1
            setting_line = await self.process_page(page_param, check)
            if setting_line:
                self.settings.append(setting_line)
            id_extend_port = self._check_extend_port(setting_line)
            if id_extend_port is not None:
                extended_ports.append(id_extend_port)
        await self.add_extra_config(extended_ports)

    async def save_config_to_file(self):
        """Сохранение конфигурации контроллера в файл."""
        async with aiofiles.open(
                self.config_file_path, 'w', encoding='cp1251') as fh:
            for line in self.settings:
                await fh.write(line)

    async def set_config(self, line_config: str):
        """Отправка настроек контроллера в виде строки по URL."""
        _LOGGER.warning(line_config)
        try:
            _LOGGER.debug(f'Попытка записи конфигурации на контроллер. '
                          f'URL: {self.url}, params: {line_config}')
            response = await self.request_to_megad(line_config)
            _LOGGER.debug(f'Статус: {response.status}. Ответ контроллера: '
                          f'{await response.text(encoding="cp1251")}')
        except Exception as e:
            raise WriteConfigError(e)

    async def upload_config(self):
        """Загрузка конфигурации на контроллер"""
        for config in self.settings:
            config = config.strip()
            if not config:
                continue
            await self.set_config(config)
            if 'nr=1' not in config:
                await asyncio.sleep(1)

    async def read_config_file(self, path: str):
        """Читает конфигурацию из файла и обновляет её у объекта"""
        async with aiofiles.open(path, "r", encoding="cp1251") as file:
            self.settings = await file.readlines()
            _LOGGER.debug(f'Прочитана конфигурация MegaD из файла: {path}')

    async def create_config_megad(self) -> DeviceMegaD:
        """Создаёт конфигурацию контроллера."""
        ports = []
        pids = []
        configs = {}
        for setting in self.settings:
            params = dict(
                parse_qsl(setting, keep_blank_values=True, encoding='cp1251')
            )
            if params.get('cf', '') in ('1', '2'):
                configs = configs | params
            elif params.get('pty') == '255':
                ports.append(PortConfig(**params))
            elif params.get('pty') == '0':
                ports.append(PortInConfig(**params))
            elif params.get('pty') == '1':
                if params.get('m') in ('0', '3'):
                    ports.append(PortOutRelayConfig(**params))
                elif params.get('m') == '1':
                    ports.append(PortOutPWMConfig(**params))
            elif params.get('pty') == '3':
                if params.get('d') == '3':
                    ports.append(OneWireSensorConfig(**params))
                elif params.get('d') == '4':
                    ports.append(IButtonConfig(**params))
                elif params.get('d') == '6':
                    if params.get('m') == '1':
                        ports.append(WiegandD0Config(**params))
                    else:
                        ports.append(WiegandConfig(**params))
                elif params.get('d') in ('1', '2'):
                    ports.append(DHTSensorConfig(**params))
                else:
                    ports.append(PortSensorConfig(**params))
            elif params.get('pty') == '4':
                if params.get('m') == '1':
                    ports.append(I2CSDAConfig(**params))
                else:
                    ports.append(I2CConfig(**params))
            elif params.get('pty') == '2':
                ports.append(AnalogPortConfig(**params))
            elif params.get('cf') == '11':
                pids.append(PIDConfig(**params))

        return DeviceMegaD(
            plc=SystemConfigMegaD(**configs), pids=pids, ports=ports
        )
