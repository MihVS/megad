import asyncio
import os

from config.custom_components.megad.const import PATH_CONFIG_MEGAD


async def get_list_config_megad(first_file='') -> list:
    """Возвращает список сохранённых файлов конфигураций контроллера"""
    config_list = await asyncio.to_thread(os.listdir, PATH_CONFIG_MEGAD)
    list_file = [file for file in config_list if file != ".gitkeep"]
    list_file.sort()
    if first_file:
        list_file.remove(first_file)
        list_file.insert(0, first_file)
    return list_file
