import logging

from .exceptions import UpdateStateError
from .models_megad import PIDConfig
from ..const import (
    P_FACTOR, I_FACTOR, D_FACTOR, VALUE_PID, INPUT_PID, TARGET_TEMP
)

_LOGGER = logging.getLogger(__name__)


class PIDControl:
    """Класс для ПИД регуляторов."""
    def __init__(self, conf, megad_id):
        self.megad_id = megad_id
        self.conf: PIDConfig = conf
        self._status: bool = False
        self._state: dict = {}

    @property
    def state(self):
        return self._state

    @property
    def status(self) -> bool:
        return False if self._state.get(INPUT_PID) == 255 else True

    @status.setter
    def status(self, value: bool):
        if isinstance(value, bool):
            self._status = value

    @property
    def p(self) -> float:
        return self._state.get(P_FACTOR, 0.0)

    @p.setter
    def p(self, value: float):
        self._state.update({P_FACTOR: value})

    @property
    def i(self) -> float:
        return self._state.get(I_FACTOR, 0.0)

    @i.setter
    def i(self, value: float):
        self._state.update({I_FACTOR: value})

    @property
    def d(self) -> float:
        return self._state.get(D_FACTOR, 0.0)

    @d.setter
    def d(self, value: float):
        self._state.update({D_FACTOR: value})

    @property
    def target_temp(self) -> int:
        return self._state.get(TARGET_TEMP)

    @target_temp.setter
    def target_temp(self, value: float):
        self._state.update({TARGET_TEMP: value})

    @property
    def value(self) -> int | None:
        return self._state.get(VALUE_PID, None)

    def _check_data(self, data: dict):
        """Проверяем корректность всех ключей данных"""
        valid_keys = list(self.conf.model_fields.keys())
        for key in data:
            if key not in valid_keys:
                raise UpdateStateError

    def _check_status(self, data: dict):
        """
        Проверяет наличие поля input в data и при необходимости меняет status
        """
        if INPUT_PID in data:
            self._status = False if data.get(INPUT_PID) == 255 else True

    def update_state(self, data: dict | PIDConfig):
        """
        Обрабатывает данные, полученные от контроллера.
        data: PIDConfig
              {'input': 255, 'set_point': 27.0}
        """
        try:
            if isinstance(data, PIDConfig):
                data = data.model_dump()
            if isinstance(data, dict):
                self._check_data(data)
                self._state.update(data)
                self._check_status(data)
            else:
                raise UpdateStateError

        except UpdateStateError:
            _LOGGER.warning(f'Megad id={self.megad_id}. Получен неизвестный '
                            f'формат данных для ПИД (id={self.conf.id}): '
                            f'{data}')
        except Exception as e:
            _LOGGER.error(f'Megad id={self.megad_id}. Ошибка при обработке '
                          f'данных ПИД №{self.conf.id}. data = {data}. '
                          f'Исключение: {e}')

    def __repr__(self):
        return (f'<PID(megad_id={self.megad_id}, id={self.conf.id}, '
                f'device_class={self.conf.device_class}, name={self.conf.name}'
                f' state={self._state})>')
