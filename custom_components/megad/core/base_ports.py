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


class BinaryPortIn(BasePort):
    """
    http://192.168.113.171:5001/megad?pt=1&m=1&cnt=2&mdid=55555 P
    http://192.168.113.171:5001/megad?pt=1&m=1&cnt=1&mdid=55555 R
    http://192.168.113.171:5001/megad?pt=2&cnt=1&mdid=55555 pr
    http://192.168.113.171:5001/megad?pt=2&m=1&cnt=2&mdid=55555 PR
    http://192.168.113.171:5001/megad?pt=1&click=1&cnt=4&mdid=55555 C
    http://192.168.113.171:5001/megad?pt=1&m=1&cnt=6&mdid=55555

    /megad?pt=1&cnt=1&mdid=55555 press

    /megad?pt=2&cnt=1&mdid=55555 PR нажат
    /megad?pt=2&m=1&cnt=2&mdid=55555 PR отжат

    /megad?pt=3&m=1&cnt=1&mdid=55555 release
    """

    def __init__(self, conf: PortInConfig):
        super().__init__(conf)
        self.conf: PortInConfig = conf
        self._state: bool = False
        self._count: int = 0

    @property
    def count(self):
        return self._count

    def update_state(self, raw_data: str):
        """raw data: OFF/7"""

        pattern = r"^[a-zA-Z0-9]+/\d+$"
        if not re.match(pattern, raw_data):
            raise UpdateStateError(f'invalid state port_in: {raw_data}')

        state, count = raw_data.split('/')

        match state:
            case 'ON' | '1':
                state = True
            case _:
                state = False

        self._state = not state if self.conf.inverse else state

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

