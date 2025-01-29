import asyncio
import os


async def get_list_config_megad(first_file='', path='') -> list:
    """Возвращает список сохранённых файлов конфигураций контроллера"""
    config_list = await asyncio.to_thread(os.listdir, path)
    list_file = [file for file in config_list if file != ".gitkeep"]
    list_file.sort()
    if first_file:
        list_file.remove(first_file)
        list_file.insert(0, first_file)
    return list_file
