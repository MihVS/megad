import asyncio
import logging
import os
import re
import socket
import time
import zipfile
from http import HTTPStatus

import requests

from .const_fw import (
    BROADCAST_PORT, RECV_PORT, BROADCAST_STRING, SEARCH_TIMEOUT,
    DEFAULT_IP_LIST, FW_PATH, BROADCAST_REBOOT, CHECK_DATA, BROADCAST_CLEAR,
    BLOCK_SIZE, BROADCAST_EEPROM, BROADCAST_EEPROM_CONFIRM
)
from .exceptions import (
    SearchMegaDError, InvalidIpAddress, InvalidPasswordMegad,
    ChangeIPMegaDError, CreateSocketReceiveError, CreateSocketSendError
)

_LOGGER = logging.getLogger(__name__)


async def get_list_config_megad(first_file='', path='') -> list:
    """Возвращает список сохранённых файлов конфигураций контроллера"""
    config_list = await asyncio.to_thread(os.listdir, path)
    list_file = [file for file in config_list if file != ".gitkeep"]
    list_file.sort()
    if first_file:
        list_file.remove(first_file)
        list_file.insert(0, first_file)
    return list_file


def get_action_turnoff(actions: str) -> str:
    """Преобразует поле Action в команду выключения всех портов"""
    new_actions = []
    actions = actions.split(';')
    for action in actions:
        if ':' in action:
            port, _ = action.split(':')
            new_actions.append(f'{port}:0')
    new_actions = list(set(new_actions))
    return ';'.join(new_actions)


def get_broadcast_ip(local_ip):
    """Преобразуем локальный IP-адрес в широковещательный."""
    return re.sub(r"(\d+)\.(\d+)\.(\d+)\.(\d+)", r"\1.\2.\3.255", local_ip)


def get_megad_ip(local_ip, broadcast_ip) -> list:
    """Получаем список адресов доступных устройств в сети."""
    ip_megads = []

    sock = create_send_socket()

    recv_sock = create_receive_socket(local_ip)
    recv_sock.settimeout(SEARCH_TIMEOUT)
    _LOGGER.info(f'Поиск устройств MegaD в сети...')
    try:
        sock.sendto(BROADCAST_STRING, (broadcast_ip, BROADCAST_PORT))
    except Exception as e:
        _LOGGER.error(f'Ошибка поиска устройств MegaD: {e}')
        sock.close()
        recv_sock.close()
        raise SearchMegaDError

    try:
        while True:
            try:
                pkt, addr = recv_sock.recvfrom(1024)
                _LOGGER.debug(f'Получен пакет от Megad {addr}: {pkt.hex()}')
                if pkt and pkt[0] == 0xAA:
                    if len(pkt) == 5:
                        ip_address = f'{pkt[1]}.{pkt[2]}.{pkt[3]}.{pkt[4]}'
                        _LOGGER.info(f'Найдено устройство с адресом: '
                                     f'{ip_address}')
                        ip_megads.append(ip_address)
                    elif len(pkt) >= 7:
                        if pkt[2] == 12:
                            if pkt[3] == 255 and pkt[4] == 255 and pkt[
                                5] == 255 and pkt[6] == 255:
                                _LOGGER.debug(f'192.168.0.14 (default '
                                              f'ip-address, bootloader mode)')
                            else:
                                ip_address = (f"{pkt[3]}.{pkt[4]}.{pkt[5]}."
                                              f"{pkt[6]} (bootloader mode)")
                                _LOGGER.debug(ip_address)
                        else:
                            ip_address = f"{pkt[1]}.{pkt[2]}.{pkt[3]}.{pkt[4]}"
                            _LOGGER.debug(ip_address)
                    else:
                        _LOGGER.warning(f'Invalid packet length: {len(pkt)}')
                else:
                    _LOGGER.warning(f'Invalid packet header: {pkt[0]:02X}')
            except socket.timeout:
                _LOGGER.info(f'Поиск устройств завершён.')
                break
    finally:
        sock.close()
        recv_sock.close()
        _LOGGER.info(f'Найденные устройства: {ip_megads}')
        return ip_megads if ip_megads else DEFAULT_IP_LIST


def change_ip(old_ip, new_ip, password, broadcast_ip):
    try:
        old_device_ip = list(map(int, old_ip.split(".")))
        new_device_ip = list(map(int, new_ip.split(".")))
    except ValueError:
        _LOGGER.error(f'Неверный формат IP-адреса: {old_ip} или {new_ip}')
        raise InvalidIpAddress

    broadcast_string = password.ljust(5, "\0")
    broadcast_string += "".join(chr(octet) for octet in old_device_ip)
    broadcast_string += "".join(chr(octet) for octet in new_device_ip)

    broadcast_string = broadcast_string.encode('latin1')

    _LOGGER.debug(f'Broadcast string (bytes): {list(broadcast_string)}')

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    sock.bind(('0.0.0.0', RECV_PORT))

    broadcast_string_old = b"\xAA\x00\x04" + broadcast_string
    sock.sendto(broadcast_string_old, (broadcast_ip, BROADCAST_PORT))
    time.sleep(0.1)

    sock.settimeout(1)
    try:
        _LOGGER.info('Попытка изменить IP-адрес. Первый запрос к контроллеру.')
        pkt, addr = sock.recvfrom(10)
        if pkt[0] == 0xAA:
            if pkt[1] == 0x01:
                _LOGGER.info(f'IP-адрес был успешно изменён!')
            elif pkt[1] == 0x02:
                sock.close()
                raise InvalidPasswordMegad
            return
    except socket.timeout:
        _LOGGER.info(f'Нет ответа от первого запроса к контроллеру. '
                     f'Возможно адрес был изменён.')

    broadcast_string_new = b"\xAA\x00\x04\xDA\xCA" + broadcast_string
    sock.sendto(broadcast_string_new, (broadcast_ip, BROADCAST_PORT))
    time.sleep(0.1)

    try:
        _LOGGER.info('Попытка изменить IP-адрес. Второй запрос к контроллеру.')
        pkt, addr = sock.recvfrom(10)
        if pkt[0] == 0xAA:
            if pkt[1] == 0x01:
                _LOGGER.info(f'IP-адрес был успешно изменён!')
            elif pkt[1] == 0x02:
                sock.close()
                raise InvalidPasswordMegad
            return
    except socket.timeout:
        sock.close()
        _LOGGER.info(f'Нет ответа от второго запроса к контроллеру. '
                     f'Возможно адрес был изменён.')
        raise ChangeIPMegaDError

    sock.close()


def create_receive_socket(host_ip) -> socket.socket:
    """Создаёт сокет для приёма данных от контроллера."""
    try:
        receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receive_socket.bind( (host_ip, RECV_PORT))

        _LOGGER.debug('Сокет для приема данных создан и привязан.')
        return receive_socket
    except Exception as e:
        _LOGGER.warning(f'Ошибка при создании сокета для приема данных: {e}')
        raise CreateSocketReceiveError


def create_send_socket() -> socket.socket:
    """Создаёт сокет для отправки данных на контроллер."""
    try:
        send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        send_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        _LOGGER.debug('Сокет для отправки данных создан.')
        return send_socket
    except Exception as e:
        _LOGGER.warning(f'Ошибка при создании сокета для отправки данных: {e}')
        raise CreateSocketSendError


def turn_on_fw_update(megad_ip: str, password: str) -> None:
    """Перевод контроллера в режим прошивки."""
    _LOGGER.debug(f'Перевод контроллера в режим прошивки...')
    try:
        requests.get(f"http://{megad_ip}/{password}/?fwup=1", timeout=1)
        time.sleep(0.01)
    except Exception as e:
        _LOGGER.debug(f'Контроллер переведён в режим прошивки.')


def download_fw(link: str, progress: dict) -> str:
    """Скачивает прошивку, распаковывает её и возвращает путь к файлу."""
    if not os.path.exists(FW_PATH):
        os.makedirs(FW_PATH)
    progress['percentage'] = 1
    name_zip_file = link.split('/')[-1]
    zip_path = os.path.join(FW_PATH, name_zip_file)

    _LOGGER.debug(f'Попытка скачать прошивку по url: {link}')
    response = requests.get(link)
    progress['percentage'] = 2
    if response.status_code == HTTPStatus.OK:
        with open(zip_path, 'wb') as file:
            file.write(response.content)
            _LOGGER.debug(f'Архив прошивки успешно скачан: {zip_path}')
    else:
        _LOGGER.warning(f'Ошибка: Не удалось скачать файл прошивки MegaD. '
                        f'Код статуса: {response.status_code}')
        raise Exception('Ошибка скачивания файла.')
    progress['percentage'] = 6

    _LOGGER.debug('Распаковка файла...')
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(FW_PATH)
        progress['percentage'] = 7

    _LOGGER.debug('Удаление архива...')
    os.remove(zip_path)
    progress['percentage'] = 8

    for file_name in os.listdir(FW_PATH):
        file_path = os.path.join(FW_PATH, file_name)
        if os.path.isfile(file_path) and file_name != os.path.basename(link):
            _LOGGER.debug(f'Разархивированный файл: {file_path}')
            progress['percentage'] = 10
            return file_path

    raise FileNotFoundError('Не удалось найти разархивированный файл.')


def check_bootloader_version(megad_ip: str, password: str):
    """Проверка загрузчика."""
    try:
        url = f'http://{megad_ip}/{password}/?bl=1'
        time.sleep(0.2)
        response = requests.get(url)
        value = int(response.text)
        if value != 1:
            raise Exception
    except Exception as e:
        _LOGGER.warning(f'Обновите загрузчик на контроллере! error: {e}')
        raise Exception('Версия загрузчика устарела!')


def reboot_megad(
        send_socket: socket.socket,
        receive_socket: socket.socket,
        broadcast_ip: str
):
    """Отправка широковещательного сообщения для перезагрузки контроллера."""
    _LOGGER.debug('Попытка перезагрузить устройство...')
    broadcast_string = BROADCAST_REBOOT + CHECK_DATA
    send_socket.sendto(broadcast_string, (broadcast_ip, BROADCAST_PORT))
    receive_socket.recvfrom(200)
    _LOGGER.info('Устройство перезагружено.')


def write_firmware(
        send_socket: socket.socket,
        receive_socket: socket.socket,
        broadcast_ip: str,
        firmware: bytes,
        progress: dict,
):
    """Запись прошивки на контроллер."""
    _LOGGER.debug(f'Стирание старой прошивки...')
    broadcast_string = BROADCAST_CLEAR + CHECK_DATA
    send_socket.sendto(broadcast_string, (broadcast_ip, BROADCAST_PORT))
    progress['percentage'] = 20
    try:
        receive_socket.settimeout(5)
        pkt, peer = receive_socket.recvfrom(200)

        if pkt[0] == 0xAA and pkt[1] == 0x00:
            _LOGGER.debug(f'Прошивка стёрта, ответ: {pkt} peer {peer}')
            progress['percentage'] = 21
            _LOGGER.debug(f'Начало записи новой прошивки...')

            firmware_blocks = [firmware[i:i + BLOCK_SIZE] for i in range(
                0, len(firmware), BLOCK_SIZE)]

            receive_socket.settimeout(2)

            msg_id = 0
            progress['percentage'] = 22

            for i, block in enumerate(firmware_blocks):
                percent_fw = int((i * 58) / (len(firmware_blocks)))
                broadcast_string = bytes(
                    [0xAA, msg_id, 0x01]) + CHECK_DATA + block
                send_socket.sendto(
                    broadcast_string, (broadcast_ip, BROADCAST_PORT)
                )
                try:
                    pkt, peer = receive_socket.recvfrom(10)
                    progress['percentage'] = percent_fw + 23

                    if pkt[0] != 0xAA or pkt[1] != msg_id:
                        _LOGGER.error(f'Ошибка прошивки устройства. Пожалуйста'
                                      f' прошейте контроллер в режиме '
                                      f'восстановления.')
                        raise Exception('Ошибка во время записи ПО...')
                except socket.timeout:
                    _LOGGER.error(f'Контроллер не ответил во время прошивки.')
                    raise Exception('Ошибка во время записи ПО...')

                msg_id = (msg_id + 1) % 256

        else:
            _LOGGER.error('Не удалось прошить устройство.')
            raise Exception('Ошибка во время записи ПО...')
    except socket.timeout:
        _LOGGER.error('Таймаут в ожидании подтверждения стирания прошивки.')
        raise Exception('Не удалось стереть прошивку')

    _LOGGER.debug('Отправка команды на стирание EEPROM')
    broadcast_string = BROADCAST_EEPROM + CHECK_DATA
    send_socket.sendto(broadcast_string, (broadcast_ip, BROADCAST_PORT))
    progress['percentage'] = 81
    try:
        receive_socket.settimeout(30)
        receive_socket.recvfrom(200)
        _LOGGER.debug('Отправка команды на подтверждение стирание EEPROM')
        broadcast_string = BROADCAST_EEPROM_CONFIRM + CHECK_DATA
        send_socket.sendto(broadcast_string, (broadcast_ip, BROADCAST_PORT))
        progress['percentage'] = 82
        pkt, peer = receive_socket.recvfrom(200)
        if pkt[0] == 0xAA and pkt[1] == 0x01:
            _LOGGER.debug('EEPROM успешно стёрта.')
        else:
            _LOGGER.error('Ошибка стирания EEPROM.')
            raise Exception('Ошибка стирания EEPROM.')

    except socket.timeout:
        _LOGGER.error('Таймаут ожидания ответа для очистки EEPROM.')
        raise Exception('Таймаут ожидания ответа для очистки EEPROM.')
