from homeassistant.exceptions import HomeAssistantError


class UpdateStateError(Exception):
    """Неверный формат данных"""
    pass


class InvalidIpAddress(Exception):
    """Ошибка валидации ip адреса"""
    pass


class WriteConfigError(Exception):
    """Ошибка записи конфигурации в контроллер"""
    pass
