from abc import ABC, abstractmethod


class BasePort(ABC):
    """Абстрактный класс для всех портов."""
    def __init__(self, conf):

        self.conf = conf
        self.state = None

    @abstractmethod
    def get_state(self, raw_data):
        """
        Обрабатывает данные, полученные от контроллера.
        Этот метод обязателен для реализации в каждом подклассе.
        """
        pass

    def __repr__(self):
        """Удобный вывод информации о порте."""
        return f"<Port(id={self.config.id}, type={self.config.type_port}, state={self.state})>"
