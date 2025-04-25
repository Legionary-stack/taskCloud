from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, NamedTuple

from requests.models import Response


class ListFilesResult(NamedTuple):
    """Результат получения списка файлов."""

    response: Response
    files: list[dict[str, Any]] | None


class CloudClient(ABC):
    """Абстрактный класс для работы с облачными Дисками"""

    @abstractmethod
    def check_disk_access(self) -> Response:
        """Проверяет доступ к облаку"""
        pass

    def _ensure_path_exists(self, remote_path: Path | None) -> bool | str:
        """Рекурсивно создает путь к файлу/папке, если его не существует"""
        raise NotImplementedError("Реализация в дочернем классе")

    def _path_exists(self, path: Path | None) -> bool:
        """Проверяет, существует ли путь на Диске"""
        raise NotImplementedError("Реализация в дочернем классе")

    @abstractmethod
    def upload_file(self, local_path: Path | None, remote_path: Path | None) -> Response:
        """Загружает файл в облако"""
        pass

    @abstractmethod
    def upload_folder(self, local_folder: Path | None, remote_folder: Path | None) -> list[Response]:
        """Загружает папку в облако"""
        pass

    @abstractmethod
    def download_file(self, remote_path: Path | None, local_path: Path | None) -> Response:
        """Скачивает файл из облака"""
        pass

    @abstractmethod
    def list_files(self, remote_path: Path | None = None) -> ListFilesResult:
        """Список файлов в облаке"""
        pass
