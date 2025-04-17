import os
from typing import List, Optional, Tuple

import requests
from dotenv import load_dotenv
from requests.models import Response

from client.cloud import CloudClient


class YandexDiskClient(CloudClient):
    def __init__(self) -> None:
        self.headers = self._initialize_headers()
        self.base_url = "https://cloud-api.yandex.net/v1/disk"

    @staticmethod
    def _initialize_headers() -> dict:
        """Инициализация заголовков с токеном доступа"""
        load_dotenv("token.env")
        yandex_access_token = os.getenv("YANDEX_ACCESS_TOKEN")

        if not yandex_access_token:
            raise ValueError("Не найден YANDEX_ACCESS_TOKEN в .env файле")

        return {
            "Authorization": f"OAuth {yandex_access_token}",
            "Accept": "application/json",
        }

    def check_disk_access(self) -> Response:
        """Проверка доступности Диска"""
        return requests.get(self.base_url, headers=self.headers)

    def _ensure_path_exists(self, remote_path: str) -> bool:
        """Рекурсивно создает путь к файлу/папке, если его не существует"""
        parts = remote_path.split("/")
        current_path = ""

        for part in parts:
            if not part:
                continue

            current_path = f"{current_path}/{part}" if current_path else part
            if not self._path_exists(current_path):
                response = requests.put(
                    f"{self.base_url}/resources?path={current_path}",
                    headers=self.headers,
                )
                if response.status_code not in (200, 201):
                    raise Exception(
                        f"Ошибка при создании папки {current_path}:"
                        f" {response.status_code} - {response.text}"
                    )

        return True

    def _path_exists(self, path: str) -> bool:
        """Проверяет, существует ли путь на Яндекс Диске"""
        response = requests.get(
            f"{self.base_url}/resources?path={path}", headers=self.headers
        )
        return response.status_code == 200

    def upload_file(self, local_path: str, remote_path: str) -> Response:
        """Загрузка файла на Диск"""
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Локальный файл не найден: {local_path}")

        self._ensure_path_exists(os.path.dirname(remote_path))

        response = requests.get(
            f"{self.base_url}/resources/upload?path={remote_path}"
            f"&overwrite=true",
            headers=self.headers,
        )

        if response.status_code != 200:
            return response

        upload_url = response.json().get("href")

        with open(local_path, "rb") as f:
            response = requests.put(upload_url, files={"file": f})

        return response

    def upload_folder(
        self, local_folder: str, remote_folder: str
    ) -> List[Response]:
        """Рекурсивная загрузка папки с содержимым"""
        responses = []

        if not os.path.isdir(local_folder):
            raise NotADirectoryError(
                f"Локальная папка не найдена:" f" {local_folder}"
            )

        self._ensure_path_exists(remote_folder)

        for root, dirs, files in os.walk(local_folder):
            for dir_name in dirs:
                local_dir_path = os.path.join(root, dir_name)
                relative_path = os.path.relpath(local_dir_path, local_folder)
                remote_dir_path = os.path.join(
                    remote_folder, relative_path
                ).replace("\\", "/")

                response = requests.put(
                    f"{self.base_url}/resources?path={remote_dir_path}",
                    headers=self.headers,
                )
                responses.append(response)

            for file_name in files:
                local_file_path = os.path.join(root, file_name)
                relative_path = os.path.relpath(local_file_path, local_folder)
                remote_file_path = os.path.join(
                    remote_folder, relative_path
                ).replace("\\", "/")

                response = self.upload_file(local_file_path, remote_file_path)
                responses.append(response)

        return responses

    def download_file(self, remote_path: str, local_path: str) -> Response:
        """Скачивание файла с Диска с полной обработкой ошибок"""
        try:
            if not remote_path:
                raise ValueError("Не указан путь к файлу на Яндекс Диске")

            response = requests.get(
                f"{self.base_url}/resources/download?path={remote_path}",
                headers=self.headers,
            )

            if response.status_code != 200:
                error_msg = response.json().get("message", "Ошибка")
                raise Exception(
                    f"Яндекс.Диск вернул ошибку: {error_msg}"
                    f" (код {response.status_code})"
                )

            download_url = response.json().get("href")
            if not download_url:
                raise Exception("Не удалось получить URL для скачивания")

            file_response = requests.get(download_url, stream=True)
            if file_response.status_code != 200:
                raise Exception(
                    f"Ошибка при загрузке файла:"
                    f" {file_response.status_code}"
                )

            if not local_path:
                local_path = os.path.basename(remote_path)

            local_dir = os.path.dirname(local_path)
            if local_dir and not os.path.exists(local_dir):
                os.makedirs(local_dir)

            with open(local_path, "wb") as f:
                for chunk in file_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            print(f"Файл успешно скачан: {remote_path} -> {local_path}")
            return file_response

        except Exception as e:
            print(f"Ошибка при скачивании файла: {str(e)}")
            raise

    def list_files(
        self, remote_path: str = ""
    ) -> Tuple[Response, Optional[list]]:
        """Получение списка файлов на Диске"""
        response = requests.get(
            f"{self.base_url}/resources?path={remote_path}&limit=1000",
            headers=self.headers,
        )

        if response.status_code != 200:
            return response, None

        items = response.json().get("_embedded", {}).get("items", [])
        return response, items
