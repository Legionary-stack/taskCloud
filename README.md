# Cloud Backup Uploader

Этот проект позволяет загружать файлы на Яндекс и Гугл Диск, скачивать файлы и папки,
просматривать список файлов в облаке.
Программа использует API Яндекс и Гугл Диска для выполнения операций.

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
3. **Создайте файлы yandexSettings.env и googleSettings.env в корне проекта и добавьте ваш токен доступа**
    ```env
   YANDEX_ACCESS_TOKEN=y0__...
   YANDEX_BASE_URL=https://cloud-api.yandex.net/v1/disk
   YANDEX_RESOURCES_ENDPOINT=/resources
   YANDEX_UPLOAD_ENDPOINT=/resources/upload
   YANDEX_DOWNLOAD_ENDPOINT=/resources/download
   ```
   ```env
   GOOGLE_ACCESS_TOKEN=ya29...
   GOOGLE_BASE_URL=https://www.googleapis.com/drive/v3
   GOOGLE_UPLOAD_URL=https://www.googleapis.com/upload/drive/v3/files
   GOOGLE_RESOURCES_ENDPOINT=/files
   GOOGLE_MIME_TYPE=application/vnd.google-apps.folder
   ```
   Чтобы получить токен:
    ```text
    https://yandex.ru/dev/disk/poligon/
    ```
   ```text
   https://developers.google.com/oauthplayground/
      ```
   (Используйте Google Drive API v3)

## Примеры Использования

```shell
python src/main.py --service google list "Google Планета Земля"
python src/main.py --service yandex list "remote/folder/path/"

python src/main.py --service google upload "local/file/path.txt" "remote/folder/path/"
python src/main.py --service yandex upload "local/file/path.txt" "remote/folder/path/"

python src/main.py --service google upload "local/folder/path" "remote/folder/path/" --type folder
python src/main.py --service yandex upload "local/folder/path" "remote/folder/path/" --type folder

python src/main.py --service google download "remote/file/path.txt" "local/save/path.txt"
python src/main.py --service yandex download "remote/file/path.txt" "local/save/path.txt"

python src/main.py --service google upload file.txt file.txt --version
python src/main.py --service google versions list file.txt
python src/main.py --service google versions download "file.txt" "ВЕРСИЯ_ID" "file.txt

пример версии_id: 0B5fr4dMW_UQgSTEwTk9MYlR0aWNDdGFObGVtVkp2c2ZsUStZPQ

```

Дополнительный запуск + Тесты
```shell
python3 -m src.main --service google list

PYTHONPATH=. pytest tests/tests_google.py -v
PYTHONPATH=. pytest tests/tests_yandex.py -v  
```

** **
- [✅] Добавлен `.gitignore`. Убедитесь, что там есть `.venv` и `.idea`
- [✅] Создано виртуальное окружение
- [✅] Есть файл `requirements.txt` или `pyproject.toml`. Исключения: если у вас нет внешних зависимостей.
- [✅] Настроены линтеры: `mypy` и `flake8`
- [✅] Настроены форматтеры: `isort` и `black`
- [✅] Написаны тесты
- [✅] Написана документация к каждому методу, классу и функции
- [✅] Написан красивый `README.md` (для форматирования можно использовать markdown), где есть информация о том, как
  проект установить и запустить, что он делает и умеет, какие фунции там есть
- [✅] (Для консольных утилит) написан help

**Авторы**

Банников Максим и Попов Георгий КН-203