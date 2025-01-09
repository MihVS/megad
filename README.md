## MegaD для Home Assistant
*Неофициальная версия интеграции.*

![python version](https://img.shields.io/badge/Python-3.13-yellowgreen?style=plastic&logo=python)
![pydantic version](https://img.shields.io/badge/pydantic-ha-yellowgreen?style=plastic&logo=fastapi)
![aiohttp version](https://img.shields.io/badge/aiohttp-ha-yellowgreen?style=plastic)
![Home Assistant](https://img.shields.io/badge/HomeAssistant-latest-yellowgreen?style=plastic&logo=homeassistant)

#### Поддержать разработку

[![Donate](https://img.shields.io/badge/donate-Tinkoff-FFDD2D.svg)](https://www.tinkoff.ru/rm/shutov.mikhail19/wUyu873109)

## Описание
Компонент для управления устройствами [MegaD](https://ab-log.ru/) из Home Assistant. 
Главная идея интеграция - как можно проще для пользователя.

> [!WARNING]
> Интеграция находится на начальной стадии разработки.
> Ниже приведён функционал на данный момент.
 
## Возможности 
### Конфигурация
Интеграция умеет сохранять конфигурацию контроллера и записывать её обратно в MegaD.
Если что-то случится с устройством, то можно заменить его и записать сохранённую 
конфигурацию. И не придётся настраивать всё вручную.

## В планах 

- [ ] Добавление бинарных сенсоров с настройкой класса устройства для НА
- [ ] Добавление сенсоров кнопок с поддержкой одиночного, двойного, долгого нажатий
- [ ] Добавление релейных выходов с настройкой класса устройства для НА
- [ ] Добавление 1wire сенсоров
- [ ] Добавление сенсоров dht сенсоров
- [ ] Добавление I2C сенсоров

*Свои предложения можете писать в issues*
