import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from requests.models import Response

from client.cloud import CloudClient


class GoogleDriveClient(CloudClient):
    def __init__(self) -> None:
        self.headers = self._initialize_headers()
        self.base_url = "https://www.googleapis.com/drive/v3"
        self.upload_url = "https://www.googleapis.com/upload/drive/v3/files"

    @staticmethod
    def _initialize_headers() -> dict:
        """Инициализация заголовков с токеном доступа"""
        load_dotenv("token.env")
        google_access_token = os.getenv("GOOGLE_ACCESS_TOKEN")

        if not google_access_token:
            raise ValueError("Не найден GOOGLE_ACCESS_TOKEN в .env файле")

        return {
            "Authorization": f"Bearer {google_access_token}",
            "Accept": "application/json",
        }

    def check_disk_access(self) -> Response:
        """Проверка доступности Google Drive"""
        return requests.get(
            f"{self.base_url}/about?fields=user", headers=self.headers
        )

    def _ensure_path_exists(self, remote_path: str) -> str:
        """
        Создает папки (если их нет) и возвращает ID последней папки в пути
        """
        if not remote_path:
            return "root"

        parent_id = "root"
        parts = [p for p in remote_path.split("/") if p]

        for part in parts:
            query = {
                "q": f"name='{part}' and '{parent_id}' in parents "
                f"and mimeType='application/vnd.google-apps.folder' "
                f"and trashed=false",
                "fields": "files(id)",
            }
            response = requests.get(
                f"{self.base_url}/files", headers=self.headers, params=query
            )
            folders = response.json().get("files", [])

            if folders:
                parent_id = folders[0]["id"]
            else:
                metadata = {
                    "name": part,
                    "mimeType": "application/vnd.google-apps.folder",
                    "parents": [parent_id],
                }
                response = requests.post(
                    f"{self.base_url}/files",
                    headers=self.headers,
                    json=metadata,
                )
                parent_id = response.json()["id"]

        return parent_id

    def _path_exists(self, path: str) -> bool:
        """Проверяет существование файла/папки"""
        if not path:
            return False

        filename = Path(path).name
        parent_path = str(Path(path).parent)
        parent_id = self._ensure_path_exists(parent_path)

        query = {
            "q": f"name='{filename}' and '{parent_id}'"
            f" in parents and trashed=false",
            "fields": "files(id)",
        }
        response = requests.get(
            f"{self.base_url}/files", headers=self.headers, params=query
        )
        return bool(response.json().get("files"))

    def upload_file(self, local_path: str, remote_path: str) -> Response:
        """Загрузка файла на Google Drive"""
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Локальный файл не найден: {local_path}")

        parent_id = self._ensure_path_exists(os.path.dirname(remote_path))
        filename = os.path.basename(remote_path)

        metadata = {"name": filename, "parents": [parent_id]}

        with open(local_path, "rb") as f:
            files: Dict[str, Tuple[str, Any, str]] = {
                "metadata": ("metadata", str(metadata), "application/json"),
                "file": (filename, f, "application/octet-stream"),
            }
            response = requests.post(
                f"{self.upload_url}?uploadType=multipart",
                headers=self.headers,
                files=files,
            )

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

        root_folder_id = self._ensure_path_exists(remote_folder)

        folder_stack = [(local_folder, root_folder_id)]

        while folder_stack:
            current_local, current_remote_id = folder_stack.pop()

            for item in os.listdir(current_local):
                local_path = os.path.join(current_local, item)
                relative_path = os.path.relpath(local_path, local_folder)
                remote_path = os.path.join(
                    remote_folder, relative_path
                ).replace("\\", "/")

                if os.path.isdir(local_path):
                    metadata = {
                        "name": item,
                        "mimeType": "application/vnd.google-apps.folder",
                        "parents": [current_remote_id],
                    }
                    response = requests.post(
                        f"{self.base_url}/files",
                        headers=self.headers,
                        json=metadata,
                    )
                    responses.append(response)

                    if response.status_code == 200:
                        folder_stack.append(
                            (local_path, response.json()["id"])
                        )
                else:
                    response = self.upload_file(local_path, remote_path)
                    responses.append(response)

        return responses

    def download_file(self, remote_path: str, local_path: str) -> Response:
        """Скачивание файла с Google Drive"""
        try:
            if not remote_path:
                raise ValueError("Не указан путь к файлу на Google Drive")

            filename = Path(remote_path).name
            parent_path = str(Path(remote_path).parent)
            parent_id = self._ensure_path_exists(parent_path)

            query = {
                "q": f"name='{filename}' and '{parent_id}'"
                f" in parents and trashed=false",
                "fields": "files(id)",
            }
            response = requests.get(
                f"{self.base_url}/files", headers=self.headers, params=query
            )
            files = response.json().get("files", [])

            if not files:
                raise FileNotFoundError(f"Файл '{remote_path}' не найден")

            file_id = files[0]["id"]

            if not local_path:
                local_path = filename

            local_dir = os.path.dirname(local_path)
            if local_dir:
                os.makedirs(local_dir, exist_ok=True)

            response = requests.get(
                f"{self.base_url}/files/{file_id}?alt=media",
                headers=self.headers,
                stream=True,
            )

            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            return response

        except Exception as e:
            print(f"Ошибка при скачивании файла: {str(e)}")
            raise

    def list_files(
        self, remote_path: str = ""
    ) -> Tuple[Response, Optional[list]]:
        """Получение списка файлов в указанной папке"""
        try:
            parent_id = self._ensure_path_exists(remote_path)
            query = {
                "q": f"'{parent_id}' in parents and trashed=false",
                "fields": "files(id,name,mimeType,size,modifiedTime)",
            }
            response = requests.get(
                f"{self.base_url}/files", headers=self.headers, params=query
            )
            return response, response.json().get("files")
        except Exception as e:
            print(f"Ошибка при получении списка файлов: {str(e)}")
            raise
