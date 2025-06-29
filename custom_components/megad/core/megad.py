import asyncio
import logging
from datetime import datetime
from http import HTTPStatus
from typing import Union

import async_timeout
from aiohttp import ClientResponse

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .base_pids import PIDControl
from .base_ports import (
    BinaryPortIn, ReleyPortOut, PWMPortOut, BinaryPortClick, BinaryPortCount,
    BasePort, OneWireSensorPort, DHTSensorPort, OneWireBusSensorPort,
    I2CSensorSCD4x, I2CSensorSTH31, AnalogSensor, I2CSensorHTUxxD,
    I2CSensorMBx280, I2CExtraMCP230xx, I2CExtraPCA9685, ReaderPort,
    I2CSensorINA226
)
from .config_parser import (
    get_uptime, async_get_page_config, get_temperature_megad,
    get_version_software, async_get_page_port, get_set_temp_thermostat,
    get_status_thermostat, async_get_page, get_params_pid, get_latest_version,
    get_names_i2c
)
from .enums import (
    TypePortMegaD, ModeInMegaD, ModeOutMegaD, TypeDSensorMegaD, DeviceI2CMegaD,
    ModeI2CMegaD, ModeSensorMegaD, ModeWiegandMegaD
)
from .exceptions import (
    MegaDBusy, InvalidPasswordMegad, FirmwareUpdateInProgress
)
from .models_megad import DeviceMegaD, PIDConfig, LatestVersionMegaD
from .request_to_ablogru import FirmwareChecker
from ..const import (
    MAIN_CONFIG, START_CONFIG, TIME_OUT_UPDATE_DATA, PORT, COMMAND, ALL_STATES,
    LIST_STATES, SCL_PORT, I2C_DEVICE, TIME_SLEEP_REQUEST, SET_TEMPERATURE,
    STATUS_THERMO, CONFIG, PID, NOT_AVAILABLE, PID_E, PID_SET_POINT, PID_INPUT,
    PID_OFF, CRON, SET_TIME, MCP_MODUL, PCA_MODUL, GET_STATUS, SCAN
)

_LOGGER = logging.getLogger(__name__)


class MegaD:
    """Класс контроллера MegaD"""

    def __init__(
            self,
            hass: HomeAssistant,
            config: DeviceMegaD,
            url: str,
            config_path: str,
            fw_checker: FirmwareChecker,
    ):
        self.hass = hass
        self.fw_checker: FirmwareChecker = fw_checker
        self.session = async_get_clientsession(hass)
        self.config: DeviceMegaD = config
        self.id = config.plc.megad_id
        self.pids: list[PIDControl] = []
        self.ports: list[Union[
            BinaryPortIn, BinaryPortClick, BinaryPortCount, ReleyPortOut,
            PWMPortOut, OneWireSensorPort, DHTSensorPort, OneWireBusSensorPort,
            I2CSensorSCD4x, I2CSensorSTH31, I2CSensorHTUxxD, AnalogSensor,
            I2CSensorMBx280, I2CExtraMCP230xx, I2CExtraPCA9685, ReaderPort,
            I2CSensorINA226
        ]] = []
        self.extra_ports: list[Union[I2CExtraMCP230xx, I2CExtraPCA9685]]
        self.config_ports_bus_i2c = []
        self.url: str = url
        self.config_path: str = config_path
        self.domain: str = url.split('/')[2]
        self.uptime: int = 0
        self.temperature: float = 0
        self.software: str | None = None
        self.lt_version_sw: LatestVersionMegaD = LatestVersionMegaD()
        self.is_flashing = False
        self.init_ports()
        self.init_pids()
        _LOGGER.debug(f'Создан объект MegaD: {self}')

    def __repr__(self):
        return (f"<MegaD(id={self.config.plc.megad_id}, "
                f"ip={self.config.plc.ip_megad}, ports={self.ports})>")

    async def update_latest_software(self):
        """Обновляет последнею доступную версию ПО контроллера"""
        page = self.fw_checker.page_firmware
        if page:
            lt_vers = get_latest_version(page, self.software)
            self.lt_version_sw = LatestVersionMegaD(**lt_vers)
            _LOGGER.debug(f'Последняя доступная версия прошивки для '
                          f'MegaD-{self.id}: {self.lt_version_sw.name}.')
            _LOGGER.debug(f'Время обновление данных о доступных прошивках: '
                          f'{self.fw_checker._last_check}')
        else:
            _LOGGER.debug('Нет данных о последней доступной версии прошивки на'
                          ' сайте ab-log.ru')

    async def request_to_megad(self, params) -> ClientResponse:
        """Отправка запроса к контроллеру"""
        if self.is_flashing:
            _LOGGER.warning(f'Управление контроллером MegaD-{self.id}'
                            f'{self.config.plc.ip_megad}  невозможно! '
                            f'Идет процесс прошивки!')
            raise FirmwareUpdateInProgress
        async with async_timeout.timeout(TIME_OUT_UPDATE_DATA):
            response = await self.session.get(url=self.url, params=params)
            _LOGGER.debug(f'Отправлен запрос контроллеру '
                          f'id {self.id}: {params}')
        return response

    async def get_status(self, params: dict) -> str:
        """Получение статуса по переданным параметрам"""
        response = await self.request_to_megad(params)
        if response.status == HTTPStatus.UNAUTHORIZED:
            _LOGGER.error(f'Неверный пароль для устройства с id {self.id}')
            raise InvalidPasswordMegad(f'Проверьте пароль у устройства '
                                       f'с id {self.id}')
        return await response.text()

    async def get_status_ports(self) -> str:
        """Запрос состояния всех портов"""
        params = {COMMAND: ALL_STATES}
        text = await self.get_status(params)
        _LOGGER.debug(f'Состояние всех портов id:{self.id}: {text}')
        return text

    async def update_data(self):
        """Обновление всех данных контроллера."""
        if self.is_flashing:
            _LOGGER.debug(f'Контроллер {self.config.plc.ip_megad} в процессе '
                          f'обновления ПО. Обновление данных невозможно.')
            return
        await self.update_current_time()
        await self.update_ports()
        await asyncio.sleep(TIME_SLEEP_REQUEST)
        page_cf0 = await async_get_page_config(
            START_CONFIG, self.url, self.session
        )
        self.software = get_version_software(page_cf0)
        _LOGGER.debug(f'Версия ПО контроллера id: {self.id}: {self.software}')

        await self.fw_checker.update_page_firmwares()
        await self.update_latest_software()

        await asyncio.sleep(TIME_SLEEP_REQUEST)
        page_cf1 = await async_get_page_config(
            MAIN_CONFIG, self.url, self.session
        )
        self.uptime = get_uptime(page_cf1)
        _LOGGER.debug(f'Время работы контроллера id:{self.id}: {self.uptime}')
        self.temperature = get_temperature_megad(page_cf1)
        _LOGGER.debug(f'Температура платы контролера '
                      f'id:{self.id}: {self.temperature}')
        if self.pids:
            await self.update_pids()

    async def update_current_time(self):
        """Синхронизирует время контроллера с сервером раз в сутки"""
        now = datetime.now().time()
        control_time_min = datetime.strptime("02:00", "%H:%M").time()
        control_time_max = datetime.strptime("02:01", "%H:%M").time()
        if control_time_max > now >= control_time_min:
            await self.set_current_time()

    async def update_pids(self):
        """Обновление данных ПИД регуляторов"""
        for pid in self.pids:
            params = {CONFIG: 11, PID: pid.conf.id}
            page = await async_get_page(
                params=params, url=self.url, session=self.session
            )
            if page != NOT_AVAILABLE:
                params_pid = get_params_pid(page)
                conf_pid = PIDConfig(**params_pid)
                pid.update_state(conf_pid)
                _LOGGER.debug(f'Обновлённые данные ПИД регулятора '
                              f'{pid.conf.id}: {conf_pid.model_dump()}')

    @staticmethod
    def check_port_is_thermostat(port) -> bool:
        """Проверка является ли порт термостатом"""
        if isinstance(port, OneWireSensorPort):
            if (
                    port.conf.mode == ModeSensorMegaD.LESS_AND_MORE
                    and port.conf.execute_action
            ):
                return True
        return False

    async def update_ports(self):
        """Обновление данных настроенных портов"""
        status_ports_raw = await self.get_status_ports()
        status_ports = status_ports_raw.split(';')
        for port in self.ports:
            state = status_ports[port.conf.id]
            if self.check_port_is_thermostat(port):
                await asyncio.sleep(TIME_SLEEP_REQUEST)
                page = await async_get_page_port(
                    port.conf.id, self.url, self.session
                )
                status = get_status_thermostat(page)
                set_temperature = get_set_temp_thermostat(page)
                port.update_state({STATUS_THERMO: status})
                port.conf.set_value = set_temperature
                _LOGGER.debug(f'Состояние терморегулятора порта '
                              f'№{port.conf.id}: статус - {status}, заданная'
                              f'температура - {set_temperature}')
            if state in (MCP_MODUL, PCA_MODUL):
                await asyncio.sleep(TIME_SLEEP_REQUEST)
                state = await self.get_status(
                    {PORT: port.conf.id, COMMAND: GET_STATUS}
                )
                port.update_state(state)
            elif state:
                port.update_state(state)
            elif isinstance(port, OneWireBusSensorPort):
                await asyncio.sleep(TIME_SLEEP_REQUEST)
                state = await self.get_status_one_wire_bus(port)
                port.update_state(state)

            # elif isinstance(port, I2CSensorSCD4x):
            #     await asyncio.sleep(TIME_SLEEP_REQUEST)
            #     state = await self.get_status_scd4x(port)
            #     port.update_state(state)

    async def get_status_one_wire_bus(self, port: OneWireBusSensorPort) -> str:
        """Обновление шины сенсоров порта 1 wire"""
        params = {PORT: port.conf.id, COMMAND: LIST_STATES}
        text = await self.get_status(params)
        _LOGGER.debug(f'Состояние 1 wire bus {self.id}-{port.conf.name}: '
                      f'{text}')
        return text

    # Нужно подумать над реализацией опроса I2C подключенных шиной.
    # !Префикс добавлен для создания уникальных id

    # async def get_status_scd4x(self, port: I2CSensorSCD4x) -> str:
    #     """Обновление сенсора СО2 типа SCD4x"""
    #     params = {
    #         PORT: port.conf.id,
    #         SCL_PORT: port.conf.scl,
    #         I2C_DEVICE: port.conf.device
    #     }
    #     text = await self.get_status(params)
    #     _LOGGER.debug(f'Состояние I2C сенсора {self.id}-{port.conf.name}: '
    #                   f'{text}')
    #     return text

    def init_ports(self):
        """Инициализация портов. Разделение их на устройства."""
        for port in self.config.ports:
            if (
                    port.type_port == TypePortMegaD.IN
                    and (port.mode == ModeInMegaD.P_R or
                         port.always_send_to_server)
            ):
                self.ports.append(BinaryPortIn(port, self.id))
            elif (
                    port.type_port == TypePortMegaD.IN
                    and port.mode == ModeInMegaD.C
            ):
                self.ports.append(BinaryPortClick(port, self.id))
            elif port.type_port == TypePortMegaD.IN:
                self.ports.append(BinaryPortCount(port, self.id))
            elif (
                    port.type_port == TypePortMegaD.OUT
                    and (port.mode in (ModeOutMegaD.SW, ModeOutMegaD.SW_LINK))
            ):
                self.ports.append(ReleyPortOut(port, self.id))
            elif (
                    port.type_port == TypePortMegaD.OUT
                    and (port.mode in (ModeOutMegaD.PWM, ))
            ):
                self.ports.append(PWMPortOut(port, self.id))
            elif port.type_port == TypePortMegaD.DSEN:
                match port.type_sensor:
                    case TypeDSensorMegaD.ONEW:
                        self.ports.append(OneWireSensorPort(port, self.id))
                    case TypeDSensorMegaD.DHT11 | TypeDSensorMegaD.DHT22:
                        self.ports.append(DHTSensorPort(port, self.id))
                    case TypeDSensorMegaD.ONEWBUS:
                        self.ports.append(OneWireBusSensorPort(port, self.id))
                    case TypeDSensorMegaD.W26:
                        if port.mode == ModeWiegandMegaD.D0:
                            self.ports.append(ReaderPort(port, self.id))
                    case TypeDSensorMegaD.iB:
                        self.ports.append(ReaderPort(port, self.id))
            elif (
                    port.type_port == TypePortMegaD.I2C
                    and port.mode == ModeI2CMegaD.SDA
            ):
                match port.device:
                    case DeviceI2CMegaD.NC:
                        self.config_ports_bus_i2c.append(port)
                    case DeviceI2CMegaD.SCD4x:
                        self.ports.append(I2CSensorSCD4x(port, self.id))
                    case DeviceI2CMegaD.SHT31:
                        self.ports.append(I2CSensorSTH31(port, self.id))
                    case DeviceI2CMegaD.HTU21D:
                        self.ports.append(I2CSensorHTUxxD(port, self.id))
                    case DeviceI2CMegaD.HTU31D:
                        self.ports.append(I2CSensorHTUxxD(port, self.id))
                    case DeviceI2CMegaD.BMx280:
                        self.ports.append(I2CSensorMBx280(port, self.id))
                    case DeviceI2CMegaD.INA226:
                        self.ports.append(I2CSensorINA226(port, self.id))
                    case DeviceI2CMegaD.MCP230XX:
                        self.ports.append(I2CExtraMCP230xx(
                            port, self.id, self.get_config_extra_ports(port)
                        ))
                    case DeviceI2CMegaD.PCA9685:
                        self.ports.append(I2CExtraPCA9685(
                            port, self.id, self.get_config_extra_ports(port)
                        ))
                    case _:
                        _LOGGER.info(f'Интеграция пока не поддерживает '
                                     f'I2C устройство: {port.device.value}. '
                                     f'Обратитесь к разработчику.')
            elif port.type_port == TypePortMegaD.ADC:
                self.ports.append(AnalogSensor(port, self.id))

        _LOGGER.debug(f'Инициализированные порты: {self.ports}')
        if self.config_ports_bus_i2c:
            _LOGGER.debug(
                f'Порты с шиной сенсоров I2C: {self.config_ports_bus_i2c}'
            )

    async def get_sensors_i2c_bus(self, config_port) -> list[str]:
        """Получает список названий сенсоров I2C в шине."""
        params = {COMMAND: SCAN, PORT: config_port.id}
        response = await self.request_to_megad(params)
        page = await response.text()
        return get_names_i2c(page)

    def get_config_extra_ports(self, port):
        """Инициализация портов расширителя I2C."""
        extra_ports = [
            ext for ext in self.config.extra_ports if ext.base_port == port.id
        ]
        extra_ports.sort(key=lambda x: x.id)
        return extra_ports

    async def async_init_i2c_bus(self):
        """Инициализация портов с шиной сенсоров I2C."""
        for port in self.config_ports_bus_i2c:
            sensor_names = await self.get_sensors_i2c_bus(port)
            for i, sensor_name in enumerate(sensor_names):
                match sensor_name.lower():
                    case DeviceI2CMegaD.SCD4x.value:
                        self.ports.append(
                            I2CSensorSCD4x(port, self.id, f'_{i}')
                        )
                    case DeviceI2CMegaD.SHT31.value:
                        self.ports.append(
                            I2CSensorSTH31(port, self.id, f'_{i}')
                        )
                    case DeviceI2CMegaD.HTU21D.value:
                        self.ports.append(
                            I2CSensorHTUxxD(port, self.id, f'_{i}')
                        )
                    case DeviceI2CMegaD.HTU31D.value:
                        self.ports.append(
                            I2CSensorHTUxxD(port, self.id, f'_{i}')
                        )
                    case DeviceI2CMegaD.BMx280.value:
                        self.ports.append(
                            I2CSensorMBx280(port, self.id, f'_{i}')
                        )
                    case DeviceI2CMegaD.INA226.value:
                        self.ports.append(
                            I2CSensorINA226(port, self.id, f'_{i}')
                        )
                    case _:
                        _LOGGER.info(f'Интеграция пока не поддерживает в шине '
                                     f'I2C устройство: {sensor_name}. '
                                     f'Обратитесь к разработчику.')

    def init_pids(self, ):
        """Инициализация ПИД регуляторов."""
        for pid in self.config.pids:
            if pid.output != PID_OFF and pid.sensor_id is not None:
                self.pids.append(PIDControl(pid, self.id))
        _LOGGER.debug(f'Инициализированные ПИД регуляторы: {self.pids}')

    def update_port(self, port_id, data):
        """Обновить данные порта по его id"""
        port = self.get_port(port_id)
        if port:
            old_state = port.state
            port.update_state(data)
            new_state = port.state
            self._check_change_port(port, old_state, new_state)

    def update_pid(self, pid_id, data):
        """Обновить данные ПИД регулятора по его id."""
        pid = self.get_pid(pid_id)
        if pid:
            pid.update_state(data)

    def get_port_interrupt(self, port_id: int):
        """Проверяет, является ли порт прерыванием для расширителя портов."""
        for port in self.ports:
            if isinstance(port, I2CExtraMCP230xx):
                if port.conf.interrupt == port_id:
                    return port

    def get_port(self, port_id, ext=False):
        """Получить порт по его id."""
        if ext:
            port_ext = self.get_port_interrupt(int(port_id))
            if port_ext is not None:
                return port_ext
        return next(
            (port for port in self.ports
             if port.conf.id == int(port_id)),
            None
        )

    def get_pid(self, pid_id):
        """Получить ПИД по его id."""
        return next(
            (pid for pid in self.pids
             if pid.conf.id == int(pid_id)),
            None
        )

    async def set_pid(self, pid_id: int, commands: dict):
        """Установка новых параметров ПИД регулятора."""
        params = {CONFIG: 11, PID_E: 2, PID: pid_id}
        params.update(commands)
        response = await self.request_to_megad(params)
        text = await response.text(encoding='windows-1251')
        match text:
            case 'busy':
                _LOGGER.warning(f'Не удалось изменить параметры ПИД №{pid_id} '
                                f'на {commands}')
                raise MegaDBusy
            case _:
                _LOGGER.debug(f'Параметры ПИД №{pid_id} (MegaD-{self.id}) '
                              f'успешно изменены на {commands}')

    async def set_current_time(self):
        """Установка текущего времени сервера на контроллер."""
        now = datetime.now()
        formatted_time = now.strftime("%H:%M:%S:") + str(now.isoweekday())
        params = {CONFIG: CRON, SET_TIME: formatted_time}
        response = await self.request_to_megad(params)
        if response.status == HTTPStatus.OK:
            _LOGGER.debug(f'Время контроллера синхронизировано: '
                          f'{formatted_time}')

    async def set_temperature_pid(self, pid_id, temperature):
        """Установка заданной температуры ПИД регулятора."""
        commands = {PID_SET_POINT: temperature}
        await self.set_pid(pid_id, commands)

    async def turn_off_pid(self, pid_id):
        """Выключение ПИД регулятора."""
        commands = {PID_INPUT: PID_OFF}
        await self.set_pid(pid_id, commands)

    async def turn_on_pid(self, pid_id):
        """Включение ПИД регулятора."""
        pid = self.get_pid(pid_id)
        commands = {PID_INPUT: pid.conf.sensor_id}
        await self.set_pid(pid_id, commands)

    async def set_temperature(self, port_id, temperature):
        """Установка заданной температуры терморегулятора."""
        params = {PORT: port_id, SET_TEMPERATURE: temperature}
        response = await self.request_to_megad(params)
        text = await response.text()
        match text:
            case 'busy':
                _LOGGER.warning(f'Не удалось изменить заданную температуру '
                                f'порта №{port_id} на {temperature}')
                raise MegaDBusy
            case _:
                _LOGGER.debug(f'Заданная температура порта №{port_id} '
                              f'изменена на {temperature}')

    async def set_port(self, port_id, command):
        """Управление выходом релейным и шим."""
        params = {COMMAND: f'{port_id}:{command}'}
        response = await self.request_to_megad(params)
        text = await response.text()
        match text:
            case 'busy':
                _LOGGER.warning(f'Не удалось изменить состояние порта или '
                                f'группы портов №{port_id}. '
                                f'Команда: {command}')
                raise MegaDBusy
            case _:
                if 'g' in str(port_id):
                    _LOGGER.debug(f'Группа портов №{port_id} изменила'
                                  f' состояние на {command}')

    def _check_change_port(
            self, port: BasePort, old_state: str, new_state: str) -> bool:
        """Проверяет новое и старое состояния портов."""
        if old_state != new_state:
            _LOGGER.debug(f'Порт №{port.conf.id} - {port.conf.name}, '
                          f'устройства id:{self.id}, '
                          f'изменил состояние с {old_state} на {new_state}')
            return True
        return False

    async def send_command(self, action) -> None:
        """Отправка команды на контроллер."""
        params = {COMMAND: action}
        await self.get_status(params)
