from homeassistant.exceptions import HomeAssistantError


class UpdateStateError(Exception):
    """Неверный формат данных"""
    pass


class InvalidIpAddress(Exception):
    """Ошибка валидации ip адреса"""
    pass


class InvalidPassword(Exception):
    """Пароль слишком длинный"""
    pass


class WriteConfigError(Exception):
    """Ошибка записи конфигурации в контроллер"""
    pass


class InvalidAuthorized(Exception):
    """Ошибка авторизации контроллера"""
    pass
