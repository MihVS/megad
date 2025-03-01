import logging
import re
from abc import ABC, abstractmethod

from .const_parse import EXTRA
from .exceptions import (
    UpdateStateError, TypeSensorError, MegaDBusy, PortOFFError, PortNotInit
)
from .models_megad import (
    PortConfig, PortInConfig, PortOutRelayConfig, PortOutPWMConfig,
    OneWireSensorConfig, PortSensorConfig, DHTSensorConfig,
    OneWireBusSensorConfig, I2CConfig, AnalogPortConfig, MCP230RelayConfig,
    MCP230PortInConfig, I2CSDAConfig
)
from ..const import (
    STATE_RELAY, VALUE, RELAY_ON, MODE, COUNT, CLICK, STATE_BUTTON,
    TEMPERATURE, PLC_BUSY, HUMIDITY, PORT_OFF, CO2, DIRECTION, STATUS_THERMO,
    PORT, NOT_AVAILABLE, PRESSURE, MCP_MODUL
)

_LOGGER = logging.getLogger(__name__)


class BasePort(ABC):
    """Абстрактный класс для всех портов."""
    def __init__(self, conf, megad_id):
        self.megad_id = megad_id
        self.conf: PortConfig = conf
        self._state: str = ''

    @property
    def state(self):
        return self._state

    @abstractmethod
    def update_state(self, raw_data):
        """
        Обрабатывает данные, полученные от контроллера.
        Этот метод обязателен для реализации в каждом подклассе.
        """
        pass

    def __repr__(self):
        return (f'<Port(megad_id={self.megad_id}, id={self.conf.id}, '
                f'type={self.conf.type_port}, state={self._state}, '
                f'name={self.conf.name})>')


class BinaryPort(BasePort, ABC):
    """Базовый бинарный порт"""

    def __init__(self, conf: PortInConfig, megad_id):
        super().__init__(conf, megad_id)
        self.conf: PortInConfig = conf
        self._state: bool = False
        self._count: int = 0

    def __repr__(self):
        return (f'<Port(megad_id={self.megad_id}, id={self.conf.id}, '
                f'type={self.conf.type_port}, state={self._state}, '
                f'name={self.conf.name}, count={self._count})>')

    @property
    def count(self):
        return self._count

    @staticmethod
    def _validate_general_request_data(data: str):
        """Валидации правильного формата данных для бинарных портов"""
        pattern = r"^[a-zA-Z0-9]+/\d+$"
        if not re.match(pattern, data):
            raise UpdateStateError


class BinaryPortIn(BinaryPort):
    """Порт настроенный как бинарный сенсор"""

    def __init__(self, conf: PortInConfig, megad_id):
        super().__init__(conf, megad_id)
        self._state: bool = False

    def update_state(self, data: str | dict):
        """
        data: ON
        data: OFF/7
        data: {'pt': '1', 'm': '1', 'cnt': '6', 'mdid': '55555'}
        data: {'pt': '1', 'm': '2', 'cnt': '7', 'mdid': '55555'}
        """
        state = self._state
        count = self._count

        try:
            if isinstance(data, str):
                states = data.split('/')
                if len(states) == 1:
                    state = states[0]
                else:
                    self._validate_general_request_data(data)
                    state, count = states
                state = state.lower()
                match state:
                    case 'on' | '1':
                        state = True
                    case _:
                        state = False
            elif isinstance(data, dict):
                state = data.get(MODE)
                count = data.get(COUNT)
                match state:
                    case '1':
                        state = False
                    case '2':
                        state = (
                            not self.state if self.conf.inverse else self.state
                        )
                    case _:
                        state = True
            else:
                raise UpdateStateError

            self._state = not state if self.conf.inverse else state
            self._count = int(count)

        except UpdateStateError:
            _LOGGER.warning(f'Megad id={self.megad_id}. Получен неизвестный '
                            f'формат данных для порта binary sensor '
                            f'(id={self.conf.id}): {data}')
        except Exception as e:
            _LOGGER.error(f'Megad id={self.megad_id}. Ошибка при обработке '
                          f'данных порта №{self.conf.id}. data = {data}. '
                          f'Исключение: {e}')


class BinaryPortClick(BinaryPort):
    """Класс для порта настроенного как нажатие."""

    def __init__(self, conf: PortInConfig, megad_id):
        super().__init__(conf, megad_id)
        self._state: str = 'off'

    def _get_state(self, data: dict) -> str:
        """Получает статус кнопки из исходных данных"""
        state: str = self._state
        click = data.get(CLICK)
        long_press = data.get(MODE)

        if click:
            match click:
                case '1':
                    state = STATE_BUTTON.SINGLE
                case '2':
                    state = STATE_BUTTON.DOUBLE
                case _:
                    state = self.state
        elif long_press:
            match long_press:
                case '2':
                    state = STATE_BUTTON.LONG
                case _:
                    state = self.state
        else:
            raise UpdateStateError
        return state

    def update_state(self, data: str | dict):
        """
        data: off, single, double, long
              OFF/7
              {'pt': '1', 'click': '1', 'cnt': '6', 'mdid': '55555'}
              {'pt': '1', 'm': '2', 'cnt': '7', 'mdid': '55555'}
        """
        count = self._count
        state = self._state

        try:
            if isinstance(data, str):
                states = data.split('/')
                if len(states) == 1:
                    state = states[0].lower()
                else:
                    self._validate_general_request_data(data)
                    state, count = states
                match state:
                    case STATE_BUTTON.SINGLE:
                        state = STATE_BUTTON.SINGLE
                    case STATE_BUTTON.DOUBLE:
                        state = STATE_BUTTON.DOUBLE
                    case STATE_BUTTON.LONG:
                        state = STATE_BUTTON.LONG
                    case _:
                        state = STATE_BUTTON.OFF

            elif isinstance(data, dict):
                state = self._get_state(data)
                count = data.get(COUNT)
            else:
                raise UpdateStateError

            self._state = state
            self._count = int(count)

        except UpdateStateError:
            _LOGGER.warning(f'Megad id={self.megad_id}. Получен неизвестный '
                            f'формат данных для порта click '
                            f'(id={self.conf.id}): {data}')
        except Exception as e:
            _LOGGER.error(f'Megad id={self.megad_id}. Ошибка при обработке '
                          f'данных порта №{self.conf.id}. data = {data}. '
                          f'Исключение: {e}')


class BinaryPortCount(BinaryPort):
    """Класс настроенный как бинарный сенсор для счетчиков"""

    def __init__(self, conf: PortInConfig, megad_id):
        super().__init__(conf, megad_id)
        self._state = None

    def update_state(self, data: str | dict):
        """
        data: OFF/7
              {'pt': '3', 'm': '1', 'cnt': '3', 'mdid': '55555'}
              {'pt': '3', 'cnt': '2', 'mdid': '55555'}
              {'pt': '3', 'm': '2', 'cnt': '2', 'mdid': '55555'}
        """
        count = self._count

        try:
            if isinstance(data, str):
                self._validate_general_request_data(data)
                _, count = data.split('/')
            elif isinstance(data, dict):
                count = data.get('cnt')
            else:
                raise UpdateStateError

            self._count = int(count)

        except UpdateStateError:
            _LOGGER.warning(f'Megad id={self.megad_id}. Получен неизвестный '
                            f'формат данных для порта count '
                            f'(id={self.conf.id}): {data}')
        except Exception as e:
            _LOGGER.error(f'Megad id={self.megad_id}. Ошибка при обработке '
                          f'данных порта №{self.conf.id}. data = {data}. '
                          f'Исключение: {e}')


class ReleyPortOut(BasePort):
    """Класс для порта настроенного как релейный выход"""

    def __init__(self, conf: PortOutRelayConfig, megad_id):
        super().__init__(conf, megad_id)
        self.conf: PortOutRelayConfig = conf
        self._state: bool = False

    @staticmethod
    def _validate_general_request_data(data):
        """Валидация строковых данных общего запроса состояний"""

        if not data.lower() in STATE_RELAY:
            raise UpdateStateError

    def update_state(self, data: str | dict):
        """
        data: OFF
          {'pt': '9', 'mdid': '44', 'v': '1'}
          {'pt': '9', 'mdid': '44', 'v': '0'}
        """
        state: bool

        try:
            if isinstance(data, int):
                data = str(data)
                self._validate_general_request_data(data)
            if isinstance(data, str):
                self._validate_general_request_data(data)
                data = data.lower()
            elif isinstance(data, dict):
                data = data.get(VALUE).lower()
            else:
                raise UpdateStateError

            match data:
                case value if value in RELAY_ON:
                    state = True
                case _:
                    state = False

            self._state = not state if self.conf.inverse else state

        except UpdateStateError:
            _LOGGER.warning(f'Megad id={self.megad_id}. Получен неизвестный '
                            f'формат данных для порта relay '
                            f'(id={self.conf.id}): {data}')
        except Exception as e:
            _LOGGER.error(f'Megad id={self.megad_id}. Ошибка при обработке '
                          f'данных порта №{self.conf.id}. data = {data}. '
                          f'Исключение: {e}')


class PWMPortOut(BasePort):
    """Клас для портов с ШИМ регулированием"""

    def __init__(self, conf: PortOutPWMConfig, megad_id):
        super().__init__(conf, megad_id)
        self.conf: PortOutPWMConfig = conf
        self._state: int = 0

    def update_state(self, data: str):
        """
        data: 100
              {'pt': '12', 'mdid': '44', 'v': '250'}
        """
        try:
            if isinstance(data, str):
                value = int(data)
            elif isinstance(data, int):
                value = data
            elif isinstance(data, dict):
                value = int(data.get(VALUE))
            else:
                raise UpdateStateError

            self._state = value

        except ValueError:
            _LOGGER.warning(f'Megad id={self.megad_id}. Для ШИМ порта нельзя '
                            f'устанавливать буквенное значение. '
                            f'Порт {self.conf.id}, значение: {data}')
        except UpdateStateError:
            _LOGGER.warning(f'Megad id={self.megad_id}. Получен неизвестный '
                            f'формат данных для порта relay '
                            f'(id={self.conf.id}): {data}')
        except Exception as e:
            _LOGGER.error(f'Megad id={self.megad_id}. Ошибка при обработке '
                          f'данных порта №{self.conf.id}. data = {data}. '
                          f'Исключение: {e}')


class DigitalSensorBase(BasePort):
    """Базовый класс для цифровых сенсоров"""

    def __init__(self, conf: PortSensorConfig, megad_id):
        super().__init__(conf, megad_id)
        self.conf: PortSensorConfig = conf
        self._state: dict = {}

    @staticmethod
    def get_states(raw_data: str) -> dict:
        """Достаёт всевозможные показания датчиков из сырых данных"""
        states = {}
        if raw_data.lower() == PLC_BUSY:
            raise MegaDBusy
        if raw_data.lower() == PORT_OFF:
            raise PortOFFError
        sensors = raw_data.split('/')
        for sensor in sensors:
            category, value = sensor.split(':')
            states[category] = value if value != NOT_AVAILABLE else None
        return states

    def short_data(self, data):
        """Прописать правильную обработку короткого вида записи данных"""
        _LOGGER.info(f'Megad id={self.megad_id}. Получен сокращённый '
                     f'вариант ответа от контроллера.'
                     f' Порт {self.conf.id}, значение: {data}')

    def check_type_sensor(self, data):
        """Проверка типа сенсора по полученным данным"""
        pass

    def update_state(self, data: str):
        """
        data: temp:24/hum:43
              CO2:980/temp:25/hum:38
              temp:NA
        """
        try:
            self._state = self.get_states(data)
            if not self._state:
                raise UpdateStateError

            self.check_type_sensor(data)

        except ValueError:
            self.short_data(data)
        except MegaDBusy:
            _LOGGER.info(f'Megad id={self.megad_id}. Неуспешная попытка '
                         f'обновить данные порта id={self.conf.id}, '
                         f'Ответ = {data}')
        except PortOFFError:
            _LOGGER.warning(f'Megad id={self.megad_id}. Порт не настроен! '
                            f'Проверьте настройки порта id={self.conf.id}, '
                            f'Ответ = {data}')
        except TypeSensorError:
            _LOGGER.warning(f'Megad id={self.megad_id}. Проверьте настройки '
                            f'порта (id={self.conf.id}). data = {data}. '
                            f'Порт должен быть настроен как '
                            f'{self.conf.type_sensor}')
        except UpdateStateError:
            _LOGGER.warning(f'Megad id={self.megad_id}. Получен неизвестный '
                            f'формат данных для порта sensor '
                            f'(id={self.conf.id}): {data}')
        except Exception as e:
            _LOGGER.error(f'Megad id={self.megad_id}. Ошибка при обработке '
                          f'данных порта №{self.conf.id}. data = {data}. '
                          f'Исключение: {e}')


class OneWireSensorPort(DigitalSensorBase):
    """Клас для портов 1 wire сенсоров"""

    def __init__(self, conf: OneWireSensorConfig, megad_id):
        super().__init__(conf, megad_id)
        self.conf: OneWireSensorConfig = conf
        self._state.update({DIRECTION: False, STATUS_THERMO: True})

    def get_states(self, raw_data: str) -> dict:
        """
        data: temp:24
              {'pt': '38', 'v': '2712', 'dir': '1', 'mdid': '44'}
              {'dir': True, 'status_thermo': False}
        """
        state = self._state
        if isinstance(raw_data, dict):
            if raw_data.get(PORT) is None:
                state.update(raw_data)
                return state
            else:
                direction = bool(int(raw_data.get(DIRECTION)))
                value = int(raw_data.get(VALUE))/100
                state.update({TEMPERATURE: value, DIRECTION: direction})
                return state
        else:
            state_temperature = super().get_states(raw_data)
            state.update(state_temperature)
            return state

    def short_data(self, data):
        """Обработка данных если температура получена одним числом"""
        if data.isdigit():
            self._state[TEMPERATURE] = data
        else:
            self._state[TEMPERATURE] = None


class TempHumSensor(DigitalSensorBase):
    """Класс для сенсора с температурой и влажностью"""

    def __init__(self, conf: PortConfig, megad_id):
        super().__init__(conf, megad_id)
        self.conf: PortConfig = conf

    def short_data(self, data):
        """
        Обработка короткой записи данных сенсора
        data: 25/38
        """
        try:
            temp, hum = data.split('/')
            self._state[TEMPERATURE] = temp
            self._state[HUMIDITY] = hum
        except ValueError:
            _LOGGER.warning(f'Неизвестный формат данных {self.megad_id}-'
                            f'port{self.conf.id}: {data}')

    def check_type_sensor(self, data):
        """Проверка типа сенсора по полученным данным"""
        if data:
            if len(data.split('/')) != 2:
                raise TypeSensorError


class DHTSensorPort(TempHumSensor):
    """Клас для портов dht сенсоров"""

    def __init__(self, conf: DHTSensorConfig, megad_id):
        super().__init__(conf, megad_id)
        self.conf: DHTSensorConfig = conf

    def check_type_sensor(self, data):
        """Проверка что данные относятся к порту настроенного как dht"""
        if not all(type_sensor in self._state for type_sensor in (
                TEMPERATURE, HUMIDITY)):
            raise TypeSensorError


class OneWireBusSensorPort(DigitalSensorBase):
    """Клас для портов 1 wire сенсоров соединённых шиной"""

    def __init__(self, conf: OneWireBusSensorConfig, megad_id):
        super().__init__(conf, megad_id)
        self.conf: OneWireBusSensorConfig = conf

    @staticmethod
    def get_states(raw_data: str) -> dict:
        """
        Достаёт показания датчиков из данных шины
        raw_data: fed000412106:24.37;619303000000:24.68
        """
        states = {}
        if 'window' in raw_data:
            raise TypeSensorError
        if raw_data.lower() == PLC_BUSY:
            raise MegaDBusy
        if raw_data.lower() == PORT_OFF:
            raise PortOFFError
        sensors = raw_data.split(';')
        for sensor in sensors:
            id_sensor, value = sensor.split(':')
            states[id_sensor] = value if value != 'NA' else None
        return states


class I2CSensorXXX(DigitalSensorBase):
    """Класс для сенсора I2C интерфейса"""

    def __init__(self, conf: I2CConfig, megad_id):
        super().__init__(conf, megad_id)
        self.conf: I2CConfig = conf

    def parse_data(self, data, keys):
        """
        Общий метод обработки данных.
        data: Х/Х/Х
        """
        try:
            values = data.split('/')
            if len(values) != len(keys):
                raise ValueError
            self._state.update(dict(zip(keys, values)))
        except ValueError:
            _LOGGER.warning(f'Неизвестный формат данных {self.megad_id}-'
                            f'port{self.conf.id}: {data}')

    def check_type_sensor(self, data):
        """Проверка типа сенсора по полученным данным"""
        if data:
            if len(data.split('/')) != 3:
                raise TypeSensorError


class I2CSensorSCD4x(I2CSensorXXX):
    """Класс для сенсора типа SCD4x I2C интерфейса"""

    def short_data(self, data):
        """
        Обработка короткой записи данных сенсора
        data: 980/25/38
        """
        self.parse_data(data, [CO2, TEMPERATURE, HUMIDITY])


class I2CSensorMBx280(I2CSensorXXX):
    """Класс для сенсора типа MBx280 I2C интерфейса"""

    def short_data(self, data):
        """
        Обработка короткой записи данных сенсора
        data: 25.5/754.86/22.59
        """
        self.parse_data(data, [TEMPERATURE, PRESSURE, HUMIDITY])


class I2CSensorSTH31(TempHumSensor):
    """Класс для сенсора типа STH31 I2C интерфейса"""

    def __init__(self, conf: I2CConfig, megad_id):
        super().__init__(conf, megad_id)
        self.conf: I2CConfig = conf


class I2CSensorHTU21D(TempHumSensor):
    """Класс для сенсора типа HTU21D I2C интерфейса"""

    def __init__(self, conf: I2CConfig, megad_id):
        super().__init__(conf, megad_id)
        self.conf: I2CConfig = conf


class AnalogSensor(BasePort):
    """Класс для аналоговых сенсоров"""

    def __init__(self, conf: AnalogPortConfig, megad_id):
        super().__init__(conf, megad_id)
        self.conf: AnalogPortConfig = conf
        self._state: int = 0

    def update_state(self, data: str):
        """
        data: 224
        """
        try:
            if data.isdigit():
                self._state = data
            elif data.lower() == PLC_BUSY:
                raise MegaDBusy
            elif data.lower() == PORT_OFF:
                raise PortOFFError
            else:
                raise UpdateStateError

        except MegaDBusy:
            _LOGGER.info(f'Megad id={self.megad_id}. Неуспешная попытка '
                         f'обновить данные порта id={self.conf.id}, '
                         f'Ответ = {data}')
        except PortOFFError:
            _LOGGER.warning(f'Megad id={self.megad_id}. Порт не настроен! '
                            f'Проверьте настройки порта id={self.conf.id}, '
                            f'Ответ = {data}')
        except UpdateStateError:
            _LOGGER.warning(f'Megad id={self.megad_id}. Получен неизвестный '
                            f'формат данных для порта sensor '
                            f'(id={self.conf.id}): {data}')
        except Exception as e:
            _LOGGER.error(f'Megad id={self.megad_id}. Ошибка при обработке '
                          f'данных порта №{self.conf.id}. data = {data}. '
                          f'Исключение: {e}')


class I2CExtraMCP230xx(BasePort):
    """Порт расширения MCP230xx"""

    def __init__(self, conf, megad_id, extra_confs):
        super().__init__(conf, megad_id)
        self.conf: I2CSDAConfig = conf
        self.extra_confs: list = extra_confs
        self._state: list = []

    def __repr__(self):
        return (f'<Port(megad_id={self.megad_id}, id={self.conf.id}, '
                f'type={self.conf.type_port}, state={self._state}, '
                f'name={self.conf.name})>')

    @staticmethod
    def get_state(data: dict) -> dict[int: str]:
        """
        Получаем из параметров состояние портов.

        :return
        {1: 0, 4: 1}
        """
        states = {}
        for key, value in data.items():
            if EXTRA in key:
                id_port = int(key[3:])
                states[id_port] = int(value)
        if states:
            return states
        else:
            raise UpdateStateError

    def update_state(self, data: str | dict):
        """
        data: MCP
        data: OFF;OFF;OFF;OFF;OFF;OFF;OFF;OFF;OFF;OFF;OFF;OFF;OFF;OFF;OFF;OFF
        data: 0;0;0;0;0;0;0;0;0;0;0;0;0;0;0;0
        data: {'pt': '40', 'ext0': '1', 'mdid': '55555'}
        data: {'pt': '40', 'ext0': '1', 'ext3': '0', 'mdid': '55555'}
        """
        try:
            if isinstance(data, str):
                if data.lower() == PLC_BUSY:
                    raise MegaDBusy
                if data == MCP_MODUL:
                    return None
                list_data = data.split(';')
                if len(list_data) < 8:
                    raise UpdateStateError
                self._state = [
                    0 if st in ('0', 'OFF') else 1 for st in list_data
                ]
            elif isinstance(data, dict):
                if not self._state:
                    raise PortNotInit
                states = self.get_state(data)
                for key, value in states.items():
                    self._state[key] = value
        except PortNotInit:
            _LOGGER.info(f'Megad id={self.megad_id}. Порт id={self.conf.id} '
                         f'не инициализирован.')
        except MegaDBusy:
            _LOGGER.info(f'Megad id={self.megad_id}. Неуспешная попытка '
                         f'обновить данные порта id={self.conf.id}, '
                         f'Ответ = {data}')
        except UpdateStateError:
            _LOGGER.warning(
                f'Megad id={self.megad_id}. Получен неизвестный '
                f'формат данных для порта sensor '
                f'(id={self.conf.id}): {data}')
        except Exception as e:
            _LOGGER.error(f'Megad id={self.megad_id}. Ошибка при обработке '
                          f'данных порта №{self.conf.id}. data = {data}. '
                          f'Исключение: {e}')
