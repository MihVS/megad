import os
import re

import aiohttp
import asyncio
import aiofiles
import logging

from bs4 import BeautifulSoup
import urllib.parse

from config.custom_components.megad.const import PATH_CONFIG_MEGAD, TITLE_MEGAD
from config.custom_components.megad.core.exceptions import WriteConfigError


_LOGGER = logging.getLogger(__name__)


async def async_fetch_page(url: str, session: aiohttp.ClientSession) -> str:
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.text(encoding='cp1251')
    except aiohttp.ClientError as e:
        print(f"Error fetching {url}: {e}")


# async def async_get_page_cf1(url: str, session: aiohttp.ClientSession) -> str:
#     try:
#         async with session.get(url=url, params={'cf': 1}) as response:
#             response.raise_for_status()
#             return await response.text(encoding='windows-1251')
#     except aiohttp.ClientError as e:
#         print(f"Error get ip {url}: {e}")
#
#
# async def get_ip(url: str, session: aiohttp.ClientSession) -> str:
#     """Получить ip из страницы конфигурации №1"""
#     page_cf1 = await async_get_page_cf1(url, session)
#     soup = BeautifulSoup(page_cf1, 'lxml')
#     input_ip = soup.form.find('input', attrs={'name': 'eip'})
#     return input_ip['value']


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


async def async_process_page(
        base_url: str, page, fh, check: bool, session: aiohttp.ClientSession):
    url = ""
    page_content = await async_fetch_page(f"{base_url}?{page}", session)
    if not page_content:
        return

    soup = BeautifulSoup(page_content, 'lxml')
    for form in soup.find_all('form'):
        if form.get('style') == 'display:inline':
            continue
        for inp in form.find_all('input'):
            if inp.get('type') != "submit":
                name = inp.get('name')
                value = inp.get('value', '')
                if inp.get('type') == "checkbox":
                    value = 'on' if inp.has_attr('checked') else ''
                url += f"{name}={urllib.parse.quote(value)}&"

    for select in soup.find_all('select'):
        name = select.get('name')
        selected_option = select.find('option', selected=True)
        if selected_option:
            value = selected_option.get('value', '')
            url += f"{name}={urllib.parse.quote(value)}&"

    url = url.rstrip('&')
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
        url: str, name_file: str, session: aiohttp.ClientSession):
    base_url, pages = await async_parse_pages(url, session)
    os.makedirs(os.path.dirname(PATH_CONFIG_MEGAD), exist_ok=True)
    name_file = os.path.join(PATH_CONFIG_MEGAD, name_file)

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


async def write_config_megad(
        file_path: str, url: str, session: aiohttp.ClientSession):
    """Асинхронное чтение файла и отправка конфига на контроллер."""

    async with aiofiles.open(file_path, "r", encoding="cp1251") as file:
        lines = await file.readlines()
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
    """Преобразует поле title в правильную кодировку"""

    teg = f'&{TITLE_MEGAD}'

    if teg in input_string:
        query_params = dict(urllib.parse.parse_qsl(
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
