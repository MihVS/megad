import asyncio
import logging
import subprocess
from urllib.parse import quote, quote_from_bytes, urlencode

from propcache import cached_property

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from . import MegaDCoordinator
from .const import DOMAIN, ENTRIES, CURRENT_ENTITY_IDS, PORT, DISPLAY_COMMAND, \
    TEXT, ROW, COLUMN, SPACE
from .core.base_ports import I2CDisplayPort
from .core.enums import DeviceI2CMegaD
from .core.megad import MegaD

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback
) -> None:
    entry_id = config_entry.entry_id
    coordinator = hass.data[DOMAIN][ENTRIES][entry_id]
    megad = coordinator.megad

    displays = []

    for port in megad.ports:
        if isinstance(port, I2CDisplayPort):
            unique_id = f'{entry_id}-{megad.id}-{port.conf.id}-display'
            if port.conf.device == DeviceI2CMegaD.LCD1602:
                displays.append(DisplayLCD1602(coordinator, port, unique_id))
            if port.conf.device == DeviceI2CMegaD.SSD1306:
                displays.append(DisplaySSD1306(coordinator, port, unique_id))

    for display in displays:
        hass.data[DOMAIN][CURRENT_ENTITY_IDS][entry_id].append(
            display.unique_id)
    if displays:
        async_add_entities(displays)
        _LOGGER.debug(f'Добавлены дисплеи: {displays}')


class MegaDDisplayEntity(CoordinatorEntity, TextEntity):
    """Класс текстового поля для дисплеев."""

    def __init__(
            self, coordinator: MegaDCoordinator, port: I2CDisplayPort,
            unique_id: str
    ):
        """Инициализация."""
        super().__init__(coordinator)
        self._coordinator: MegaDCoordinator = coordinator
        self._megad: MegaD = coordinator.megad
        self._port: I2CDisplayPort = port
        self._name: str = port.conf.name
        self._unique_id = unique_id
        self.entity_id = (f'text.{self._megad.id}_port{port.conf.id}_'
                          f'{port.conf.device.value}')
        self._attr_device_info = coordinator.devices_info()

    def __repr__(self) -> str:
        if not self.hass:
            return f"<Sensor entity {self.entity_id}>"
        return super().__repr__()

    @cached_property
    def name(self) -> str:
        return self._name

    @cached_property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def native_value(self) -> str:
        """Возвращает состояние сенсора"""
        return self._port.state

    def clean_line(self) -> dict:
        """Возвращает параметры для очистки нужной строки."""
        raise NotImplementedError

    def write_line(self, line: str) -> list[dict]:
        raise NotImplementedError

    async def async_set_value(self, value: str) -> None:
        """Set the text value."""
        _LOGGER.debug(f'Текст переданный на дисплей: {value}')
        await self._megad.request_to_megad(self.clean_line())
        await asyncio.sleep(0.2)
        params_display = self.write_line(value)
        for params in params_display:
            await asyncio.sleep(0.2)
            await self._megad.request_to_megad(params)


class DisplayLCD1602(MegaDDisplayEntity):
    """Класс для двухстрочного дисплея."""

    def clean_line(self) -> dict:
        return {PORT: self._port.conf.id, DISPLAY_COMMAND: 1}

    @staticmethod
    def parse_line(line: str) -> list[dict]:
        """Преобразует строку к нужному формату для дисплея."""
        lines = line.split('/')[:2]
        prepare_lines = []
        indent: int = 0
        for line in lines:
            center: bool = line.startswith('^')
            right: bool = line.startswith('>')
            if center:
                line = line[1:16].strip('_')
                len_line = len(line)
                if len_line % 2 == 0:
                    indent = 8 - len_line // 2
                else:
                    indent = 7 - len_line // 2
            elif right:
                line = line[1:16].strip('_')
                indent = 16 - len(line)
            else:
                line = line[:16]
            prepare_lines.append(
                {'indent': indent, 'line': line.replace(' ', '_')}
            )
        return prepare_lines

    def write_line(self, line: str) -> list[dict]:
        """Возвращает список параметров для запроса к контроллеру."""
        lines = self.parse_line(line)
        list_params = []
        _LOGGER.debug(f'lines: {lines}')
        for row, key in enumerate(lines):
            list_params.append(
                {
                    PORT: self._port.conf.id,
                    TEXT: key['line'],
                    ROW: row,
                    COLUMN: key['indent']}
            )
        _LOGGER.debug(f'list_params: {list_params}')
        return list_params


class DisplaySSD1306(MegaDDisplayEntity):
    """Класс для многострочного дисплея."""

    def clean_line(self, number_of_line: int | None = None) -> dict:
        """Возвращает параметры для очистки нужной строки."""
        port_id = self._port.conf.id
        if number_of_line is None:
            return {PORT: port_id, TEXT: (6 * SPACE)}
        return {PORT: port_id, DISPLAY_COMMAND: 1, ROW: number_of_line}

    @staticmethod
    def extract_number_from_braces(s: str) -> dict:
        if s.startswith('{') and '}' in s:
            closing_brace_pos = s.find('}')
            number_part = s[1:closing_brace_pos]
            if number_part.isdigit():
                return {
                    'indent': int(number_part),
                    'line': s[closing_brace_pos + 1:]
                }
        return {'indent': 0, 'line': s}

    @staticmethod
    def center_value(value: str) -> str:
        """Центрует значение сенсора по центру экрана при большом масштабе."""
        str_len = len(value)
        if 's' in value or '_' in value:
            return value
        if 0 < str_len < 3:
            return f'ss{value}'
        elif 2 < str_len <= 5 and '.' in value:
            return f's{value}'
        elif 2 < str_len < 5:
            return f's{value}'
        else: return value

    @staticmethod
    def check_big_font(data: list[dict]) -> bool:
        """Проверяет наличие большого шифра."""
        for value in data:
            indent = value.get('indent')
            if indent is None:
                return True
        return False

    def parse_line(self, line: str) -> list[dict]:
        """Преобразует строку к нужному формату для дисплея."""
        prepare_lines = []
        if '/' in line:
            lines = line.split('/')[:4]
            for line in lines:
                prepare_lines.append(self.extract_number_from_braces(line))
        elif '\\' in line:
            lines = line.split('\\')[:3]
            for row, line in enumerate(lines):
                if row == 1:
                    prepare_lines.append(
                        {'indent': None, 'line': self.center_value(line)}
                    )
                else:
                    prepare_lines.append(self.extract_number_from_braces(line))
        else:
            prepare_lines.append({'indent': None, 'line': self.center_value(line)})
        return prepare_lines

    def write_line(self, line: str) -> list[dict]:
        """Возвращает список параметров для запроса к контроллеру."""
        lines = self.parse_line(line)
        list_params = []
        _LOGGER.debug(f'lines: {lines}')
        if self.check_big_font(lines):
            for row, key in enumerate(lines):
                if key.get('indent') is None:
                    list_params.append(
                        {
                            PORT: self._port.conf.id,
                            TEXT: key.get('line'),
                        }
                    )
                else:
                    list_params.append(
                        {
                            PORT: self._port.conf.id,
                            TEXT: key.get('line'),
                            ROW: row if row == 0 else 6,
                            COLUMN: key.get('indent'),
                        }
                    )
        else:
            for row, key in enumerate(lines):
                list_params.append(
                    {
                        PORT: self._port.conf.id,
                        TEXT: key.get('line'),
                        ROW: row * 2,
                        COLUMN: key.get('indent')
                    }
                )
        _LOGGER.debug(f'list_params: {list_params}')
        return list_params

    async def async_set_value(self, value: str) -> None:
        """Set the text value."""
        _LOGGER.debug(f'Текст переданный на дисплей: {value}')
        params_display = self.write_line(value)
        _LOGGER.debug(f'params_display: {params_display}')
        count_lines = len(params_display)
        if count_lines == 1:
            await self._megad.request_to_megad(self.clean_line())
            await asyncio.sleep(0.2)
        else:
            if params_display[1].get('row') is None:
                for i, params in enumerate(params_display):
                    if params.get('row') is None:
                        await self._megad.request_to_megad(self.clean_line())
                        await asyncio.sleep(0.2)
                    elif i == 0:
                        await self._megad.request_to_megad(self.clean_line(0))
                        await asyncio.sleep(0.2)
                    elif i == count_lines - 1:
                        await self._megad.request_to_megad(self.clean_line(6))
                        await asyncio.sleep(0.2)
            else:
                for i, params in enumerate(params_display):
                    if params.get('text') != '':
                        await self._megad.request_to_megad(
                            self.clean_line(i * 2)
                        )
                        await asyncio.sleep(0.2)
        for params in params_display:
            await asyncio.sleep(0.2)
            params_str = urlencode(params, safe='%')
            await self._megad.request_to_megad(params_str)
