import os
import shutil
import time
from typing import Generator

import pytest
import requests

from src.client.yandex_client import YandexDiskClient

TEST_FOLDER = "test_folder"
TEST_FILE = "test_file.txt"
TEST_CONTENT = "This is test file content"
TEST_LOCAL_FOLDER = "test_local_folder"


@pytest.fixture(scope="module")
def client() -> Generator[YandexDiskClient, None, None]:
    """Подготовка тестового окружения (создание и удаление папок/файлов)"""
    client = YandexDiskClient()

    response = client.check_disk_access()
    if response.status_code != 200:
        pytest.skip("Яндекс Диск недоступен (проверьте токен и подключение)")

    client._ensure_path_exists(TEST_FOLDER)

    with open(TEST_FILE, "w") as f:
        f.write(TEST_CONTENT)

    yield client

    try:
        os.remove(TEST_FILE)
        shutil.rmtree(TEST_LOCAL_FOLDER)

        response = requests.delete(
            f"{client.base_url}/resources?path=" f"{TEST_FOLDER}/&permanently=true",
            headers=client.headers,
        )
    except Exception as e:
        print(f"Ошибка при очистке тестового окружения: {str(e)}")


def test_upload_file(client: YandexDiskClient) -> None:
    """Тест загрузки файла на Яндекс Диск"""
    remote_path = f"{TEST_FOLDER}/uploaded_file.txt"

    response = client.upload_file(TEST_FILE, remote_path)
    assert response.status_code == 201 or response.status_code == 202

    response, items = client.list_files(TEST_FOLDER)
    assert items is not None
    assert any(item["name"] == "uploaded_file.txt" for item in items)


def test_upload_folder(client: YandexDiskClient) -> None:
    """Тест загрузки папки с файлами"""
    local_folder = "test_local_folder"
    remote_folder = f"{TEST_FOLDER}/uploaded_folder"

    os.makedirs(local_folder, exist_ok=True)
    for i in range(3):
        with open(f"{local_folder}/file_{i}.txt", "w") as f:
            f.write(f"Test content {i}")

    responses = client.upload_folder(local_folder, remote_folder)
    assert all(r.status_code in (200, 201, 202) for r in responses)

    response, items = client.list_files(remote_folder)
    assert items is not None
    assert len(items) == 3
    assert all(item["name"].startswith("file_") for item in items)


def test_download_file(client: YandexDiskClient) -> None:
    """Тест скачивания файла с Яндекс Диска"""
    remote_path = f"{TEST_FOLDER}/downloaded_file.txt"
    local_path = "downloaded_file.txt"

    client.upload_file(TEST_FILE, remote_path)
    time.sleep(1)

    response = client.download_file(remote_path, local_path)
    assert response.status_code == 200
    with open(local_path, "r") as f:
        content = f.read()
    assert content == TEST_CONTENT

    os.remove(local_path)


def test_list_files(client: YandexDiskClient) -> None:
    """Тест получения списка файлов"""
    for i in range(2):
        remote_path = f"{TEST_FOLDER}/list_test_{i}.txt"
        client.upload_file(TEST_FILE, remote_path)

    time.sleep(1)

    response, items = client.list_files(TEST_FOLDER)
    assert response.status_code == 200
    assert items is not None
    assert len(items) >= 2

    filenames = [item["name"] for item in items]
    assert all(f"list_test_{i}.txt" in filenames for i in range(2))


def test_path_operations(client: YandexDiskClient) -> None:
    """Тест работы с путями (создание и проверка существования)"""
    test_path = f"{TEST_FOLDER}/test/sub/folder"

    assert not client._path_exists(test_path)

    assert client._ensure_path_exists(test_path)

    assert client._path_exists(test_path)


if __name__ == "__main__":
    pytest.main()
