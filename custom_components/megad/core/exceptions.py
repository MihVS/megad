from homeassistant.exceptions import HomeAssistantError


class UpdateStateError(Exception):
    """Неверный формат данных"""
    pass


class MegaDBusy(Exception):
    """Контроллер не успел выполнить команду"""
    pass


class PortNotInit(Exception):
    """Порт не инициализирован"""
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


class InvalidMegaDID(Exception):
    """Отсутствует MegaD ID в настройках контроллера."""
    pass


class InvalidPasswordMegad(HomeAssistantError):
    """Неверный пароль для контроллера"""
    pass


class NotAvailableURL(Exception):
    """Адрес не доступен"""
    pass


class TemperatureOutOfRangeError(HomeAssistantError):
    """Задана температура не в пределах допустимого диапазона."""
    pass


class InvalidSettingPort(HomeAssistantError):
    """Неправильно настроен порт."""
    pass


class TypeSensorError(Exception):
    """Данные не соответствуют типу устройства"""
    pass


class PortOFFError(Exception):
    """Порт не настроен"""
    pass


class SetFactorPIDError(HomeAssistantError):
    """Не удалось изменить коэффициент ПИД регулятора."""
    pass


class SearchMegaDError(Exception):
    """Ошибка поиска устройства."""
    pass


class ChangeIPMegaDError(Exception):
    """Ошибка изменения адреса устройства."""
    pass
