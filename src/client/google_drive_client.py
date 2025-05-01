from __future__ import annotations

from pathlib import Path
from typing import Any

import requests
from pydantic_settings import BaseSettings, SettingsConfigDict
from requests.models import Response

from .cloud import CloudClient, ListFilesResult


class GoogleSettings(BaseSettings):
    """Настройки для Гугл Диска"""

    access_token: str
    base_url: str
    upload_url: str
    resources_endpoint: str
    mime_type: str
    model_config = SettingsConfigDict(env_file="googleSettings.env", env_prefix='GOOGLE_')


class GoogleDriveClient(CloudClient):
    """Класс для работы с Гугл Диском"""

    def __init__(self) -> None:
        self._settings = GoogleSettings()  # type: ignore
        self._headers = {
            "Authorization": f"Bearer {self._settings.access_token}",
            "Accept": "application/json",
        }
        self._mime_type = self._settings.mime_type
        self._base_url = self._settings.base_url

    def check_disk_access(self) -> Response:
        """Проверка доступности Google Drive"""
        url = f"{self._base_url}/about?fields=user"
        return requests.get(url, headers=self._headers)

    def _ensure_path_exists(self, remote_path: Path | None) -> str:
        """
        Создает папки (если их нет) и возвращает ID последней папки в пути
        """
        if not remote_path or str(remote_path) == ".":
            return "root"

        parent_id = "root"
        parts = [p for p in remote_path.parts if p != '/']

        for part in parts:
            query = {
                "q": f"name='{part}' and '{parent_id}' in parents "
                     f"and mimeType='{self._mime_type}' "
                     f"and trashed=false",
                "fields": "files(id)",
            }
            url = f"{self._base_url}{self._settings.resources_endpoint}"
            response = requests.get(url, headers=self._headers, params=query)
            folders = response.json().get("files", [])

            if folders:
                parent_id = folders[0]["id"]
            else:
                metadata = {
                    "name": part,
                    "mimeType": self._mime_type,
                    "parents": [parent_id],
                }
                url = f"{self._base_url}{self._settings.resources_endpoint}"
                response = requests.post(
                    url,
                    headers=self._headers,
                    json=metadata,
                )
                parent_id = response.json()["id"]

        return parent_id

    def _path_exists(self, path: Path | None) -> bool:
        """Проверяет существование файла/папки"""
        if not path:
            return False

        filename = path.name
        parent_path = path.parent
        parent_id = self._ensure_path_exists(parent_path)

        query = {
            "q": f"name='{filename}' and '{parent_id}' in parents and trashed=false",
            "fields": "files(id)",
        }
        url = f"{self._base_url}{self._settings.resources_endpoint}"
        response = requests.get(url, headers=self._headers, params=query)
        return bool(response.json().get("files"))

    def upload_file(
            self, local_path: Path | None, remote_path: Path | None, create_new_version: bool = False
    ) -> Response:
        """Загрузка файла на Google Drive с корректным версионированием"""
        if not local_path or not remote_path:
            raise ValueError("Локальный и удаленный пути не могут быть None")

        if not local_path.exists():
            raise FileNotFoundError(f"Локальный файл не найден: {local_path}")
        print(create_new_version)

        file_id = None
        if create_new_version:
            try:
                file_id = self._get_file_id(remote_path)
            except FileNotFoundError:
                pass

        if file_id:
            url = f"{self._base_url}{self._settings.resources_endpoint}/{file_id}"

            file_metadata = {"name": str(remote_path.name)}
            requests.patch(url, headers=self._headers, json=file_metadata)

            update_url = f"{self._settings.upload_url}/{file_id}?uploadType=media"
            with local_path.open("rb") as f:
                return requests.patch(update_url, headers=self._headers, data=f)

        parent_id = self._ensure_path_exists(remote_path.parent)
        metadata = {"name": remote_path.name, "parents": [parent_id]}

        with local_path.open("rb") as f:
            files: dict[str, tuple[str, Any, str]] = {
                "metadata": ("metadata", str(metadata), "application/json"),
                "file": (remote_path.name, f, "application/octet-stream"),
            }
            url = f"{self._settings.upload_url}?uploadType=multipart"
            response = requests.post(
                url,
                headers=self._headers,
                files=files,
            )
            return response

    def upload_folder(self, local_folder: Path | None, remote_folder: Path | None) -> list[Response]:
        """Рекурсивная загрузка папки с содержимым"""

        if not local_folder:
            raise NotADirectoryError(f"Локальная папка не найдена: {local_folder}")

        responses = []
        root_folder_id = self._ensure_path_exists(remote_folder)
        folder_stack = [(local_folder, root_folder_id)]

        while folder_stack:
            current_local, current_remote_id = folder_stack.pop()

            for item in current_local.iterdir():
                relative_path = item.relative_to(local_folder)
                remote_item_path = Path(remote_folder) / relative_path if remote_folder else relative_path

                if item.is_dir():
                    metadata = {
                        "name": item.name,
                        "mimeType": self._mime_type,
                        "parents": [current_remote_id],
                    }
                    url = f"{self._base_url}{self._settings.resources_endpoint}"
                    response = requests.post(
                        url,
                        headers=self._headers,
                        json=metadata,
                    )
                    responses.append(response)

                    if response.status_code == 200:
                        folder_stack.append((item, response.json()["id"]))
                else:
                    response = self.upload_file(item, remote_item_path)
                    responses.append(response)

        return responses

    def download_file(self, remote_path: Path | None, local_path: Path | None) -> Response:
        """Скачивание файла с Google Drive"""
        if not remote_path:
            raise ValueError("Не указан путь к файлу на Google Drive")

        filename = remote_path.name
        parent_path = remote_path.parent
        parent_id = self._ensure_path_exists(parent_path)

        query = {
            "q": f"name='{filename}' and '{parent_id}' in parents and trashed=false",
            "fields": "files(id)",
        }

        url = f"{self._base_url}{self._settings.resources_endpoint}"
        response = requests.get(url, headers=self._headers, params=query)
        files = response.json().get("files", [])

        if not files:
            raise FileNotFoundError(f"Файл '{remote_path}' не найден")

        file_id = files[0]["id"]
        download_path = local_path if local_path else Path(filename)

        if download_path.parent:
            download_path.parent.mkdir(parents=True, exist_ok=True)

        response = requests.get(
            f"{url}/{file_id}?alt=media",
            headers=self._headers,
            stream=True,
        )

        with download_path.open("wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return response

    def list_files(self, remote_path: Path | None = None) -> ListFilesResult:
        """Получение списка файлов в указанной папке"""
        parent_id = self._ensure_path_exists(remote_path)
        query = {
            "q": f"'{parent_id}' in parents and trashed=false",
            "fields": "files(id,name,mimeType,size,modifiedTime)",
        }
        url = f"{self._base_url}{self._settings.resources_endpoint}"
        response = requests.get(url, headers=self._headers, params=query)
        return ListFilesResult(response=response, files=response.json().get("files", []))

    def list_file_versions(self, file_id: str) -> ListFilesResult:
        """Получить список версий файла"""
        url = f"{self._base_url}{self._settings.resources_endpoint}/{file_id}/revisions"
        response = requests.get(url, headers=self._headers)
        return ListFilesResult(response=response, files=response.json().get("revisions", []))

    def download_version(self, file_id: str, version_id: str, local_path: Path) -> Response:
        """Скачать конкретную версию файла"""
        url = f"{self._base_url}{self._settings.resources_endpoint}/{file_id}/revisions/{version_id}?alt=media"
        response = requests.get(url, headers=self._headers, stream=True)

        with local_path.open("wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return response

    def _get_file_id(self, remote_path: Path) -> str:
        """Получить ID файла по пути"""
        if not remote_path:
            raise ValueError("Не указан путь к файлу")

        filename = remote_path.name
        parent_path = remote_path.parent
        parent_id = self._ensure_path_exists(parent_path)

        query = {
            "q": f"name='{filename}' and '{parent_id}' in parents and trashed=false",
            "fields": "files(id)",
        }
        url = f"{self._base_url}{self._settings.resources_endpoint}"
        response = requests.get(url, headers=self._headers, params=query)
        files = response.json().get("files", [])

        if not files:
            raise FileNotFoundError(f"Файл '{remote_path}' не найден")

        file_id: str = str(files[0]["id"])
        return file_id
