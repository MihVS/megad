import asyncio
import logging
import os
import re
from datetime import timedelta
from urllib.parse import parse_qsl

import aiofiles
import aiohttp
from bs4 import BeautifulSoup

from .exceptions import WriteConfigError
from .models_megad import (
    DeviceMegaD, PortConfig, PortInConfig, PortOutRelayConfig,
    PortOutPWMConfig, OneWireSensorConfig, IButtonConfig, WiegandD0Config,
    WiegandConfig, DHTSensorConfig, PortSensorConfig, I2CSDAConfig, I2CConfig,
    AnalogPortConfig, SystemConfigMegaD, PIDConfig
)
from ..const import (
    TITLE_MEGAD, NAME_SCRIPT_MEGAD, CONFIG, PORT
)

_LOGGER = logging.getLogger(__name__)


async def async_fetch_page(url: str, session: aiohttp.ClientSession) -> str:
    """Получение страницы конфигурации контроллера"""

    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text(encoding='cp1251')


async def async_get_page(
        params: dict, url: str, session: aiohttp.ClientSession
) -> str:
    """Получение страницы конфигурации контроллера"""
    async with session.get(url=url, params=params) as response:
        response.raise_for_status()
        return await response.text(encoding='windows-1251')


async def async_get_page_port(
        port_id: int, url: str, session: aiohttp.ClientSession) -> str:
    """Получение страницы конфигурации порта контроллера"""
    return await async_get_page({PORT: port_id}, url, session)


async def async_get_page_config(
        cf: int, url: str, session: aiohttp.ClientSession) -> str:
    """Получение страницы конкретной конфигурации контроллера"""
    return await async_get_page({CONFIG: cf}, url, session)


def get_status_thermostat(page: str) -> bool:
    """Получает включенное состояние порта термостата"""
    soup = BeautifulSoup(page, 'lxml')
    select_mode = soup.find('select', {'name': 'm'})
    return False if 'DIS' in select_mode.next_sibling else True


def get_set_temp_thermostat(page: str) -> float:
    """Получить установленную температуру термостата"""
    soup = BeautifulSoup(page, 'lxml')
    val_input = soup.find('input', {'name': 'misc'})
    return float(val_input.get('value'))

def get_uptime(page_cf: str) -> int:
    """Получить время работы контроллера в минутах"""
    soup = BeautifulSoup(page_cf, 'lxml')
    uptime_text = soup.find(string=lambda text: "Uptime" in text)
    if uptime_text:
        uptime = uptime_text.replace("Uptime:", "").strip()
        days, time = uptime.split('d')
        days = int(days.strip())
        hours, minutes = map(int, time.strip().split(':'))
        delta = timedelta(days=days, hours=hours, minutes=minutes)
        total_minutes = int(delta.total_seconds() / 60)
        return total_minutes
    return -1


def get_temperature_megad(page_cf: str) -> float:
    """Получить температуру на плате контроллера"""

    soup = BeautifulSoup(page_cf, 'lxml')
    temp_text = soup.find(string=lambda text: "Temp" in text)
    if temp_text:
        temperature = temp_text.replace("Temp:", "").strip()
        return float(temperature)
    return -100


def get_version_software(page_cf: str) -> str:
    """Получить версию прошивки контроллера"""

    soup = BeautifulSoup(page_cf, 'lxml')
    software_text = soup.find(string=lambda text: '(fw:' in text)
    software = software_text.replace("(fw:", "").strip().strip(')')
    return software


async def get_slug_server(page_cf: str) -> str:
    """Получает поле script в интерфейсе конфигурации megad"""

    soup = BeautifulSoup(page_cf, 'lxml')
    teg = soup.find('input', {'name': NAME_SCRIPT_MEGAD})
    return teg.get('value')


async def async_parse_pages(url: str, session: aiohttp.ClientSession):
    pages = ["cf=1", "cf=2", "cf=7", "cf=8"]

    first_page = await async_fetch_page(url, session)
    if first_page and "IN/OUT" in first_page:
        ports = 45 if "[44," in first_page else 37
    else:
        ports_match = re.findall(r'/sec/\?pt=(\d+)', first_page or "")
        if ports_match:
            ports = max(
                map(int, ports_match))
        else:
            ports = 0

    pages.extend(f"pt={i}" for i in range(ports + 1))
    pages.extend(f"cf=10&prn={i}" for i in range(10))
    pages.extend(f"cf=11&pid={i}" for i in range(5))
    pages.extend(f"cf=6&sc={i}" for i in range(5))
    pages.extend(f"cf=6&el={i}" for i in range(16))

    return url, pages


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


def get_params_pid(page: str) -> dict:
    """Получает параметры настройки ПИД регулятора из страницы"""
    params = dict(
        parse_qsl(get_params(page), keep_blank_values=True, encoding='cp1251')
    )
    value = ''
    soup = BeautifulSoup(page, 'lxml')
    for br in soup.find_all('br'):
        text = str(br.next_sibling)
        if 'Val:' in text:
            value = text.split('Val:')[-1].strip()
    params.update({'value': value})
    return params


async def async_process_page(
        base_url: str, page, fh, check: bool, session: aiohttp.ClientSession):
    page_content = await async_fetch_page(f"{base_url}?{page}", session)
    if not page_content:
        return
    url = get_params(page_content)
    if url and url != 'cf=<br':
        if not _check_url(url, check):
            url = url + '&nr=1'
            url = decode_emt(url)
        await fh.write(url + "\n")


def _check_url(url: str, check: bool) -> bool:
    if check:
        return True
    return True if "cf=1&" in url else False


async def async_read_configuration(
        url: str, name_file: str, session: aiohttp.ClientSession, path):
    """Чтение конфигурации с контроллера и запись её в файл"""
    base_url, pages = await async_parse_pages(url, session)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    name_file = os.path.join(path, name_file)

    count_line = len(pages)
    i = 1

    async with aiofiles.open(name_file, 'w', encoding='cp1251') as fh:
        for page in pages:
            check = False
            if i == count_line:
                check = True
            i += 1
            await async_process_page(base_url, page, fh, check, session)


async def send_line(url: str, line: str, session: aiohttp.ClientSession):
    """Функция для отправки строки по URL."""
    try:
        async with session.get(f'{url}?{line}') as response:
            _LOGGER.debug(f"Отправлено: {url}?{line}, "
                          f"Ответ: {await response.text(encoding="cp1251")}")
    except Exception as e:
        raise WriteConfigError(e)


async def async_read_config_file(file_path: str) -> list[str]:
    """Читает файл конфигурации и возвращает список строк"""

    async with aiofiles.open(file_path, "r", encoding="cp1251") as file:
        return await file.readlines()


async def write_config_megad(
        file_path: str, url: str, session: aiohttp.ClientSession):
    """Асинхронное чтение файла и отправка конфига на контроллер."""

    lines = await async_read_config_file(file_path)
    count_lines = len(lines)
    i = 1
    for line in lines:
        line = line.strip()
        if not line:
            continue
        await send_line(url, line, session)
        if i == 1 or i == count_lines:
            await asyncio.sleep(1)
        i += 1


def decode_emt(input_string: str) -> str:
    """Преобразует поле title в правильную кодировку для Русского языка"""

    teg = f'&{TITLE_MEGAD}'

    if teg in input_string:
        query_params = dict(parse_qsl(
            input_string, keep_blank_values=True)
        )
        emt_value = query_params[TITLE_MEGAD]
        emt_value_cp1251 = emt_value.encode('cp1251')
        emt_value_urlencoded = ''.join(
            f'%{hex(b)[2:].upper()}' if b > 127 or b in b' #%&+?/' else chr(b)
            for b in emt_value_cp1251
        )
        query_params[TITLE_MEGAD] = emt_value_urlencoded
        output_string = ''

        for key, value in query_params.items():
            output_string += f'{key}={value}&'

        return output_string[:-1]
    else:
        return input_string


async def create_config_megad(file_path: str) -> DeviceMegaD:
    """Создаёт конфигурацию контроллера из файла"""

    lines: list = await async_read_config_file(file_path)
    ports = []
    pids = []
    configs = {}
    await asyncio.sleep(0)

    for line in lines:
        params = dict(
            parse_qsl(line, keep_blank_values=True, encoding='cp1251')
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
            if params.get('pido'):
                pids.append(PIDConfig(**params))

    return DeviceMegaD(
        plc=SystemConfigMegaD(**configs), pids=pids, ports=ports
    )
