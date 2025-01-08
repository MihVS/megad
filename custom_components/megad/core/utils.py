import asyncio
import os

from config.custom_components.megad.const import PATH_CONFIG_MEGAD


async def get_list_config_megad() -> list:
    """Возвращает список сохранённых файлов конфигураций контроллера"""

    config_list = await asyncio.to_thread(os.listdir, PATH_CONFIG_MEGAD)

    return [file for file in config_list if file != ".gitkeep"]