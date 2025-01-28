## MegaD для Home Assistant
*Неофициальная версия интеграции.*

![python version](https://img.shields.io/badge/Python-3.13-yellowgreen?style=plastic&logo=python)
![pydantic version](https://img.shields.io/badge/pydantic-ha-yellowgreen?style=plastic&logo=fastapi)
![aiohttp version](https://img.shields.io/badge/aiohttp-ha-yellowgreen?style=plastic)
![Home Assistant](https://img.shields.io/badge/HomeAssistant-latest-yellowgreen?style=plastic&logo=homeassistant)

#### Поддержать разработку

[![Donate](https://img.shields.io/badge/donate-Tinkoff-FFDD2D.svg)](https://www.tinkoff.ru/rm/shutov.mikhail19/wUyu873109)

## Описание
Компонент для управления устройствами [MegaD](https://ab-log.ru/) из Home Assistant (далее НА). 
Работоспособность проверялась на прошивке версии 4.64b6 (моноблок).

> [!IMPORTANT]
> !!! Для корректной работы интеграции после каждого обновления конфигурации
> контроллера необходимо заново прочитать настройки контроллера интеграцией. 
> И выбрать сохранённый файл для обновления данных в НА. Это делается из 
> интерфейса НА кнопкой "Настроить" у устройства.

> [!WARNING]
> Интеграция находится на начальной стадии разработки.
> Ниже приведён функционал на данный момент.
 
## Возможности.
### Конфигурация.
Интеграция умеет сохранять конфигурацию контроллера и записывать её обратно в MegaD.
Если что-то случится с устройством, то можно заменить его и записать сохранённую 
конфигурацию. И не придётся настраивать всё вручную.

Для корректной работы интеграции, необходимо в главной конфигурации контроллера
указать в поле "Script" значение: megad. Тип сервера: HTTP. Адрес сервера HA
(например: 192.168.1.20:8123).


### Бинарные сенсоры.
В НА добавляются порты в качестве бинарного сенсора только те порты IN у которых в интерфейсе
MegaD в поле "Mode" стоит значение "P&R" или значения "P", "R" но если установлена
галочка ☑ у этого поля. В противном случае порт будет добавлен как [счетчик](#счётчики) или [сенсор кнопки](#сенсоры-кнопок)
В поле "Title" порта (настройка MegaD) можно указать название сенсора, его тип и инверсию.
**Помните, что контроллер ограничивает это поле 25 символами.**

Формат: имя сенсора/тип устройства/инверсия
* Имя устройства может быть любым, главное ограничение количество символов
* Тип устройства состоит из 1 или 2 букв английского алфавита. Поддерживаемые типы устройств:
    - Движение (motion) --> m
    - Окно (window) --> w
    - Дверь (door) --> d
    - Гаражные ворота (garage_door) --> gd
    - Замок (lock) --> l
    - Обнаружение влаги (moisture) --> ms
    - Обнаружение дыма (smoke) --> s
* Инверсия имеет значения 1 или 0. По умолчанию 0.

> ✳ при необходимости поддержи других типов, создавайте issues.

Примеры:
* Дверь/d --> Имя "Дверь" / Тип в НА door / инверсии нет
* Коридор/m/1 --> Имя "Коридор" / Тип в НА motion / инверсия установлена
* Плита --> Имя "Плита" / Тип в НА None / инверсии нет


### Сенсоры кнопок.

Порты IN которые настроены в режиме "Click", добавляются в НА как сенсоры кнопок.

Возможные состояния такого сенсора:
* single --> одиночное нажатие
* double --> двойное нажатие
* long --> длительное нажатие
* off --> состояние по умолчанию

### Счётчики.

У каждого порта с типом "IN" есть дополнительный параметр число срабатывания порта.
Это число добавляется в НА отдельным сенсором. Логику работы счётчика смотрите 
в [документации MegaD](https://ab-log.ru/smart-house/ethernet/megad-2561#conf-in-cnt).


### Релейные выходы.

По умолчанию релейные выходы в НА добавляются как switch. 
В поле "Title" порта (настройка MegaD) можно указать название устройства, его 
тип и инверсию. Ограничение поля по длине 25 символов.

Формат: имя сенсора/тип устройства/инверсия
* Имя устройства может быть любым, главное ограничение количество символов
* Тип устройства состоит из 1 или 2 букв английского алфавита. Поддерживаемые типы устройств:
    - Переключатель (switch) --> s
    - Освещение (light) --> l
    - Вентиляция (fan) --> f
* Инверсия имеет значения 1 или 0. По умолчанию 0. Полезна при подключении нагрузки к нормально замкнутым контактам.


### Групповые переключатели.

В настройках контроллера есть такое понятие как группы устройств. Интеграция 
добавляет такие группы как отдельный переключатель (switch). Подробней о настройке
групп смотрите в [документации](https://ab-log.ru/smart-house/ethernet/megad-2561#conf-out-gr).
Использование групповых переключателей снижает нагрузку на контроллер.

Групповой переключатель не имеет статуса состояния. 
> [!TIP]
> Инверсированые выходы при выключении группы будут переходить 
> во включенное состояние и наоборот.


Если управлять в НА через действия:
* switch.turn_on --> включает все порты в группе
* switch.turn_off --> выключает все порты в группе
* switch.toggle --> переключает состояние всех портов в группе. (даже если состояния были в разнобой)


### Диммируемые выходы.

В НА диммируемые выходы добавляются как освещение (light) с возможной установкой
яркости светильника. В настройке контроллера у выхода PWM есть поле "Min", где
можно выставить минимальное значение с которого НА начнёт управление яркостью.
Все значения ниже этой яркости для НА будут означать выключенное состояние.
Для плавного диммирования необходимо установить галочку в поле "Smooth" в 
настройках порта контроллера. Подробнее смотрите в 
[документации](https://ab-log.ru/smart-house/ethernet/megad-2561#conf-out-pwm)

Есть возможность изменить тип устройства в поле "Title".

Формат: имя сенсора/тип устройства
* Имя устройства может быть любым, главное ограничение количество символов
* Тип устройства состоит из 1 или 2 букв английского алфавита. Поддерживаемые типы устройств:
    - Освещение (light) --> l
    - Вентиляция (fan) --> f


## Сенсоры.

Показания сенсоров обновляются примерно раз в минуту.

В НА добавляются и отображаются следующие сенсоры:
1. Собственные сенсоры контроллера:
   * Температура платы
   * Uptime (продолжительность работы)
2. Сенсоры температуры 1 wire (так же подключение шиной).
3. Сенсоры температуры и влажности DHT11, DHT22
4. I2C сенсоры (перечень интегрированных в НА смотрите ниже)

### Сенсоры температуры и влажности типа 1wire и dht.

Если порт настроен как цифровой датчик "DSen" с типом сенсора "1W", "DHT11" или
"DHT22", то в НА добавляются все доступные сенсоры на этих портах. 

### I2C сенсоры.

Добавление I2C устройств сложный процесс, нужно добавлять каждый датчик отдельно.
Поэтому по мере необходимости буду их добавлять.

Поддерживаемые сенсоры:
- SCD4x (CO2, температура, влажность)
- SHT31 (температура, влажность)

## В планах

- [x] ~~Добавление бинарных сенсоров с настройкой класса устройства для НА~~
- [x] ~~Добавление сенсоров кнопок с поддержкой одиночного, двойного, долгого нажатий~~
- [x] ~~Добавление сенсоров счётчиков от портов с типом "IN"~~
- [x] ~~Добавление релейных выходов с настройкой класса устройства для НА~~
- [x] ~~Поддержка управления группами созданных в настройках контроллера~~
- [x] ~~Добавление диммируемых выходов в НА~~
- [x] ~~Функционал перезагрузки интеграции~~
- [x] ~~Функционал перенастройки интеграции~~
- [x] ~~Первый релиз интеграции для HACS~~
- [x] ~~Добавление 1wire сенсоров~~
- [x] ~~Добавление сенсоров dht сенсоров~~
- [x] ~~добавление 1wire сенсоров в шине~~
- [x] ~~Добавление I2C сенсоров~~
- [ ] Аналоговые датчики
- [ ] Добавление терморегуляторов в НА
- [ ] Обновление прошивки контроллера из НА

*Свои предложения можете писать в issues*

## Установка
**Способ 1.** [HACS](https://hacs.xyz/) -> Интеграции -> 3 точки в правом верхнем углу -> Пользовательские репозитории

Далее вставляем репозиторий https://github.com/MihVS/megad выбираем категорию "Интеграция" и жмём добавить.
***
**Способ 2.** Вручную скопируйте каталог `megad` в директорию `/config/custom_components`
***
### **Не забываем поставить ⭐ интеграции.**

## Настройка
> Настройки -> Интеграции -> Добавить интеграцию -> **MegaD-2561**
 

### Логирование.
Чтобы изменить уровень логирования, для выявления проблем, необходимо в файле `configuration.yaml` добавить:
```yaml
logger:
  logs:
    custom_components.megad: debug
```

## Разработчик
**[Михаил Шутов](https://github.com/mihvs)**