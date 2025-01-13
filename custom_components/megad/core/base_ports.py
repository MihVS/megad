from abc import ABC, abstractmethod
import re

from .exceptions import UpdateStateError
from .models_megad import (PortConfig, PortInConfig, PortOutRelayConfig,
                           PortOutPWMConfig,
                           )


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

    @property
    def count(self):
        return self._count

    def _validate_general_request_data(self, data: str):
        """Валидации правильного формата данных для бинарных портов"""

        pattern = r"^[a-zA-Z0-9]+/\d+$"
        if not re.match(pattern, data):
            raise UpdateStateError(f'Неизвестный формат данных для порта '
                                   f'BinaryPort (id={self.conf.id}): {data}')


class BinaryPortIn(BinaryPort):
    """Кла настроенный как бинарный сенсор"""

    def __init__(self, conf: PortInConfig):
        super().__init__(conf)
        self._state: bool = False

    def update_state(self, data: str | dict):
        """
        data: ON
        data: OFF/7
        data: {'pt': '1', 'm': '2', 'cnt': '7', 'mdid': '55555'}
        """

        count = self._count

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
            state = data.get('m')
            count = data.get('cnt')
            match state:
                case '1':
                    state = False
                case '2':
                    pass
                case _:
                    state = False
        else:
            raise UpdateStateError(f'Неизвестный формат данных для порта '
                                   f'binary sensor (id={self.conf.id}): '
                                   f'{data}')

        self._state = not state if self.conf.inverse else state
        self._count = int(count)


class BinaryPortClick(BinaryPort):
    """Класс для порта настроенного как нажатие."""

    def __init__(self, conf: PortInConfig):
        super().__init__(conf)
        self._state: str = 'off'

    def _get_state(self, data: dict) -> str:
        """Получает статус кнопки из исходных данных"""

        state: str = self._state
        click = data.get('click')
        long_press = data.get('m')
        if click:
            match click:
                case '1':
                    state = 'single'
                case '2':
                    state = 'double'
                case _:
                    pass
        elif long_press:
            match long_press:
                case '2':
                    state = 'long'
                case _:
                    pass
        else:
            raise UpdateStateError(f'Неизвестный формат данных для порта '
                                   f'click (id={self.conf.id}): {data}')

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

        if isinstance(data, str):
            states = data.split('/')
            if len(states) == 1:
                state = states[0].lower()
            else:
                self._validate_general_request_data(data)
                state, count = states
            match state:
                case 'single':
                    state = 'single'
                case 'double':
                    state = 'double'
                case 'long':
                    state = 'long'
                case _:
                    state = 'off'

        elif isinstance(data, dict):
            self._state = self._get_state(data)
        else:
            raise UpdateStateError(f'Неизвестный формат данных для порта '
                                   f'click (id={self.conf.id}): {data}')

        self._state = state
        self._count = int(count)


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

        if isinstance(data, str):
            self._validate_general_request_data(data)
            _, count = data.split('/')
        elif isinstance(data, dict):
            count = data.get('cnt')
        else:
            raise UpdateStateError(f'Неизвестный формат данных для порта '
                                   f'count (id={self.conf.id}): {data}')

        self._count = int(count)


class ReleyPortOut(BasePort):
    """
    http://192.168.113.171:5001/megad?pt=7&mdid=55555&v=0
    """

    def __init__(self, conf: PortOutRelayConfig):
        super().__init__(conf)
        self.conf: PortOutRelayConfig = conf
        self._state: bool = False

    def update_state(self, raw_data: str | int | bool):
        """raw data: OFF"""

        state: bool

        match raw_data:
            case 'ON' | '1' | 1:
                state = True
            case _:
                state = False

        self._state = not state if self.conf.inverse else state


class PWMPortOut(BasePort):
    """
    http://192.168.113.171:5001/megad?pt=12&mdid=55555&v=250
    """

    def __init__(self, conf: PortOutPWMConfig):
        super().__init__(conf)
        self.conf: PortOutPWMConfig = conf
        self._state: int = 0

    def update_state(self, raw_data: str | int):
        """raw data: 100"""

        self._state = int(raw_data)
