import logging
import re
from abc import ABC, abstractmethod

from .exceptions import UpdateStateError
from .models_megad import (PortConfig, PortInConfig, PortOutRelayConfig,
                           PortOutPWMConfig, OneWireSensorConfig,
                           )
from ..const import (STATE_RELAY, VALUE, RELAY_ON, MODE, COUNT, CLICK,
                     STATE_BUTTON
                     )

_LOGGER = logging.getLogger(__name__)


class BasePort(ABC):
    """Абстрактный класс для всех портов."""
    def __init__(self, conf):
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
        return (f"<Port(id={self.conf.id}, type={self.conf.type_port}, "
                f"state={self._state}), name={self.conf.name})>")


class BinaryPort(BasePort, ABC):
    """Базовый бинарный порт"""

    def __init__(self, conf: PortInConfig):
        super().__init__(conf)
        self.conf: PortInConfig = conf
        self._state: bool = False
        self._count: int = 0

    def __repr__(self):
        return (f"<Port(id={self.conf.id}, type={self.conf.type_port}, "
                f"state={self._state}), name={self.conf.name}, "
                f"count={self._count})>")

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

    def __init__(self, conf: PortInConfig):
        super().__init__(conf)
        self._state: bool = False

    def update_state(self, data: str | dict):
        """
        data: ON
        data: OFF/7
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
                        state = self.state
                    case _:
                        state = True
            else:
                raise UpdateStateError

            self._state = not state if self.conf.inverse else state
            self._count = int(count)

        except UpdateStateError:
            _LOGGER.warning(f'Получен неизвестный формат данных для порта '
                            f'binary sensor (id={self.conf.id}): {data}')
        except Exception as e:
            _LOGGER.error(f'Ошибка при обработке данных порта №{self.conf.id}.'
                          f'data = {data}. Исключение: {e}')


class BinaryPortClick(BinaryPort):
    """Класс для порта настроенного как нажатие."""

    def __init__(self, conf: PortInConfig):
        super().__init__(conf)
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
            _LOGGER.warning(f'Получен неизвестный формат данных для порта '
                            f'click (id={self.conf.id}): {data}')
        except Exception as e:
            _LOGGER.error(f'Ошибка при обработке данных порта №{self.conf.id}.'
                          f'data = {data}. Исключение: {e}')


class BinaryPortCount(BinaryPort):
    """Класс настроенный как бинарный сенсор для счетчиков"""

    def __init__(self, conf: PortInConfig):
        super().__init__(conf)
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
            _LOGGER.warning(f'Получен неизвестный формат данных для порта '
                            f'count (id={self.conf.id}): {data}')
        except Exception as e:
            _LOGGER.error(f'Ошибка при обработке данных порта №{self.conf.id}.'
                          f'data = {data}. Исключение: {e}')


class ReleyPortOut(BasePort):
    """Класс для порта настроенного как релейный выход"""

    def __init__(self, conf: PortOutRelayConfig):
        super().__init__(conf)
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
            _LOGGER.warning(f'Получен неизвестный формат данных для порта '
                            f'relay (id={self.conf.id}): {data}')
        except Exception as e:
            _LOGGER.error(f'Ошибка при обработке данных порта №{self.conf.id}.'
                          f'data = {data}. Исключение: {e}')


class PWMPortOut(BasePort):
    """Клас для портов с ШИМ регулированием"""

    def __init__(self, conf: PortOutPWMConfig):
        super().__init__(conf)
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
            _LOGGER.warning(f'Для ШИМ порта нельзя устанавливать буквенное '
                            f'значение. Порт {self.conf.id}, значение: {data}')
        except UpdateStateError:
            _LOGGER.warning(f'Получен неизвестный формат данных для порта '
                            f'relay (id={self.conf.id}), data = {data}')
        except Exception as e:
            _LOGGER.error(f'Ошибка при обработке данных порта №{self.conf.id}.'
                          f'data = {data}. Исключение: {e}')


class DSensorPortOneWire(BasePort):
    """Клас для портов 1 wire сенсоров"""

    def __init__(self, conf: OneWireSensorConfig):
        super().__init__(conf)
        self.conf: OneWireSensorConfig = conf
        self._state: dict = {}

