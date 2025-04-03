import os
import requests
from dotenv import load_dotenv
from requests.models import Response


def initialize() -> tuple[str, dict]:
    """Инициализация переменных окружения и заголовков"""
    load_dotenv("token.env")

    yandex_access_token = os.getenv("YANDEX_ACCESS_TOKEN")

    if not yandex_access_token:
        raise ValueError("Не найден YANDEX_ACCESS_TOKEN в .env файле")

    headers = {
        "Authorization": f"OAuth {yandex_access_token}",
        "Accept": "application/json"
    }

    return yandex_access_token, headers


def check_disk_access(headers: dict) -> Response:
    """Проверка доступности Диска"""
    response = requests.get(
        "https://cloud-api.yandex.net/v1/disk",
        headers=headers
    )
    return response


def create_backup_folder(folder_name: str, headers: dict) -> Response:
    """Создание папки для бэкапов"""
    response = requests.put(
        f"https://cloud-api.yandex.net/v1/disk/resources?path={folder_name}",
        headers=headers
    )
    return response


def folder_exists(folder_name: str, headers: dict) -> bool:
    """Проверка существования папки."""
    response = requests.get(
        f"https://cloud-api.yandex.net/v1/disk/resources?path={folder_name}&fields=path",
        headers=headers
    )
    return response.status_code == 200


def upload_file(local_path: str, remote_path: str, headers: dict) -> Response:
    """Загрузка файла на Диск"""
    response = requests.get(
        f"https://cloud-api.yandex.net/v1/disk/resources/upload?path={remote_path}&overwrite=true",
        headers=headers
    )

    if response.status_code != 200:
        return response

    upload_url = response.json().get("href")

    with open(local_path, 'rb') as f:
        response = requests.put(upload_url, files={'file': f})

    return response


def create_folder(folder_name: str, headers: dict) -> Response:
    """Создание папки, если она не существует."""
    response = requests.put(
        f"https://cloud-api.yandex.net/v1/disk/resources?path={folder_name}",
        headers=headers
    )
    return response


if __name__ == "__main__":
    yandex_access_token, headers = initialize()

    response = check_disk_access(headers)
    print(f"Статус проверки доступа: {response.status_code}")
    print(response.json())

    main_folder_name = "pytask"

    if not folder_exists(main_folder_name, headers):
        print(f"Создаем папку: {main_folder_name}")
        response = create_folder(main_folder_name, headers)
        print(f"Создание папки: {response.status_code}")

    local_file_path = input("Введите путь к файлу для загрузки: ")
    remote_file_path = f"{main_folder_name}/{os.path.basename(local_file_path)}"

    response = upload_file(local_file_path, remote_file_path, headers)
    print(f"Загрузка файла: {response.status_code}")
