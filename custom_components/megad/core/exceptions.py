from homeassistant.exceptions import HomeAssistantError


class UpdateStateError(Exception):
    """Неверный формат данных"""
    pass


class PortBusy(Exception):
    """Контроллер не успел выполнить команду"""
    pass


class InvalidIpAddress(Exception):
    """Ошибка валидации ip адреса"""
    pass


class InvalidIpAddressExist(Exception):
    """Ip адрес уже добавлен в НА"""
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


class InvalidSlug(Exception):
    """Неправильный slug указан в поле script контроллера."""
    pass


class InvalidPasswordMegad(HomeAssistantError):
    """Неверный пароль для контроллера"""
    pass
