import asyncio
import logging
import os
import re
import socket
import time

from .const_fw import (
    BROADCAST_PORT, RECV_PORT, BROADCAST_STRING, SEARCH_TIMEOUT,
    DEFAULT_IP_LIST
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
