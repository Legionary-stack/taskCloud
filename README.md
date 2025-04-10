# Cloud Backup Uploader

Этот проект позволяет загружать файлы на Яндекс Диск,
создавая папку для бэкапов, если она еще не существует.
Программа использует API Яндекс Диска для выполнения операций.

## Установка

1. **Клонируйте репозиторий**

   ```bash
   git clone https://github.com/Legionary-stack/taskCloud.git
   cd ваш_репозиторий
   ```
   
2. **Установите зависимости**
    ```bash
     pip install -r requirements.txt
    ```
3. **Создайте файл .env в корне проекта и добавьте ваш токен доступа**
    ```env
    YANDEX_ACCESS_TOKEN=ваш_токен
    ```
   Чтобы получить токен:
    ```text
    https://yandex.ru/dev/disk/poligon/
    ```
## Использование
1. **Запустите скрипт**
    ```text
    python main.py
    ```
2. **Введите название папки для копирования**
3. **Введите путь к файлу, который вы 
хотите загрузить на Яндекс Диск**

## Авторы
Банников Максим и Попов Георгий КН-203

