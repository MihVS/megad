from abc import ABC, abstractmethod

from .models_megad import PortMegaD, PortInMegaD


class BasePort(ABC):
    """Абстрактный класс для всех портов."""
    def __init__(self, conf):
        self.conf: PortMegaD = conf
        self.state: str = ''

    @abstractmethod
    def update_state(self, raw_data):
        """
        Обрабатывает данные, полученные от контроллера.
        Этот метод обязателен для реализации в каждом подклассе.
        """
        pass

    def __repr__(self):
        return (f"<Port(id={self.conf.id}, type={self.conf.type_port}, "
                f"state={self.state}), name={self.conf.name})>")


class InputBinary(BasePort):
    def __init__(self, conf: PortInMegaD):
        super().__init__(conf)
        self.state: bool = False
        self.count: int = 0

    def update_state(self, raw_data: str):
        """raw data: OFF/0"""

        state, count = raw_data.split('/')
        match state:
            case 'ON':
                state = True
            case _:
                state = False

        if self.conf.inverse:
            self.state = not state
        else:
            self.state = state

        self.count = int(count)

