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


def get_action_turnoff(actions: str) -> str:
    """Преобразует поле Action в команду выключения всех портов"""
    new_actions = []
    actions = actions.split(';')
    for action in actions:
        if ':' in action:
            port, _ = action.split(':')
            new_actions.append(f'{port}:0')
    new_actions = list(set(new_actions))
    return ';'.join(new_actions)

