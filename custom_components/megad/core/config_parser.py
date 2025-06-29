import logging
from datetime import timedelta
from urllib.parse import parse_qsl

import aiohttp
from bs4 import BeautifulSoup

from .config_manager import MegaDConfigManager
from ..const import NAME_SCRIPT_MEGAD, CONFIG, PORT, BASE_URL

_LOGGER = logging.getLogger(__name__)


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


async def get_megad_id_server(page_cf: str) -> str:
    """Получает Megad-ID в интерфейсе конфигурации megad"""
    soup = BeautifulSoup(page_cf, 'lxml')
    mdid_input = soup.find('input', {'name': 'mdid'})
    return mdid_input.get('value')


def get_names_i2c(page: str) -> list[str]:
    """Получает названия сенсоров I2C из html."""
    soup = BeautifulSoup(page, 'lxml')
    hrefs = soup.find_all('a')
    return [href.text for href, in hrefs[1:]]


def get_params_pid(page: str) -> dict:
    """Получает параметры настройки ПИД регулятора из страницы"""
    params = dict(parse_qsl(
        MegaDConfigManager.get_params(page),
        keep_blank_values=True,
        encoding='cp1251'
    ))
    value = ''
    soup = BeautifulSoup(page, 'lxml')
    for br in soup.find_all('br'):
        text = str(br.next_sibling)
        if 'Val:' in text:
            value = text.split('Val:')[-1].strip()
    params.update({'value': value})
    return params


def _check_name_version(full_version: str) -> str:
    """Возвращает правильный формат названия версии прошивки."""
    if 'beta' in full_version:
        version, beta = full_version.split('beta')
        return f'{version.strip()}b{beta.strip()}'
    else:
        return full_version


def create_description(versions: list[dict]) -> str:
    """Создаёт описание на основе описаний пропущенных версий."""
    description = []
    for version in versions:
        description.append(f'{version["title"]}\n{version["descr"]}\n')
    return '\n'.join(description)


def create_short_description(descr: str) -> str:
    """Создаёт краткое описание которое меньше 255 символов."""
    if len(descr) < 254:
        return descr
    else:
        return f'{descr[:251]}...'


def get_latest_version(page: str, current_version: str) -> dict:
    """Получает последнею версию ПО контроллера и описание."""
    passed_versions = []
    all_versions = []

    soup = BeautifulSoup(page, 'lxml')
    div_tag = soup.find('div', class_='cnt')
    li_tags = div_tag.find_all('li')
    for li_tag in li_tags:
        version = {}
        title = li_tag.font.text
        full_version = title.split('ver')[-1].strip()
        version['name'] = _check_name_version(full_version)
        version['title'] = title
        descr_list = []
        descrs = li_tag.find('br').next_siblings
        for el in descrs:
            if el.name == 'a':
                break
            descr_list.append(el.text)
        version['descr'] = ''.join(descr_list)
        version['link'] = f'{BASE_URL}{li_tag.find('a', href=True)['href']}'
        all_versions.append(version)

    sorted_versions = sorted(
        all_versions, key=lambda v: v['name'], reverse=True
    )
    if current_version is None:
        _LOGGER.debug('Текущая версия ПО контроллера не инициирована.')
        full_descr = ''
    else:
        for version in sorted_versions:
            if version['name'] > current_version:
                passed_versions.append(version)
        full_descr = create_description(passed_versions)
    return {
        'name': sorted_versions[0]['name'],
        'descr': full_descr if full_descr else sorted_versions[0]['descr'],
        'short_descr': create_short_description(sorted_versions[0]['descr']),
        'link': sorted_versions[0]['link']
    }
