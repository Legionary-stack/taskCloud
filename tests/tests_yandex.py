from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Generator

import pytest
import requests

from src.client.yandex_client import YandexDiskClient


@pytest.fixture(scope="module")
def client() -> Generator[YandexDiskClient, None, None]:
    client = YandexDiskClient()

    if client.check_disk_access().status_code != 200:
        pytest.skip("Яндекс.Диск недоступен (проверьте токен и подключение)")

    yield client


@pytest.fixture
def test_file() -> Generator[Path, None, None]:
    with NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("Test file content")
        file_path = Path(f.name)

    yield file_path
    file_path.unlink(missing_ok=True)


@pytest.fixture
def test_folder() -> Generator[Path, None, None]:
    with TemporaryDirectory() as temp_dir:
        dir_path = Path(temp_dir)
        for i in range(3):
            (dir_path / f"file_{i}.txt").write_text(f"Content {i}")
        yield dir_path


@pytest.fixture
def remote_test_folder(client: YandexDiskClient) -> Generator[Path, None, None]:
    folder_name = "pytest_test_folder"
    remote_path = Path(folder_name)
    client._ensure_path_exists(remote_path)

    yield remote_path

    try:
        requests.delete(f"{client._base_url}/resources?path={folder_name}&permanently=true", headers=client._headers)
    except Exception as e:
        print(f"Ошибка очистки тестовой папки: {e}")


def test_upload_file(client: YandexDiskClient, test_file: Path, remote_test_folder: Path) -> None:
    remote_path = remote_test_folder / "test_file.txt"

    response = client.upload_file(test_file, remote_path)
    assert response.status_code in (201, 202)

    _, files = client.list_files(remote_test_folder)
    assert files is not None
    assert any(f["name"] == remote_path.name for f in files)


def test_upload_folder(client: YandexDiskClient, test_folder: Path, remote_test_folder: Path) -> None:
    remote_path = remote_test_folder / "test_folder"

    responses = client.upload_folder(test_folder, remote_path)
    assert all(r.status_code in (200, 201, 202) for r in responses)

    _, files = client.list_files(remote_path)
    assert files is not None
    assert len(files) == 3


def test_download_file(client: YandexDiskClient, test_file: Path, remote_test_folder: Path) -> None:
    remote_path = remote_test_folder / "download_test.txt"
    client.upload_file(test_file, remote_path)

    with NamedTemporaryFile(delete=False) as tmp_file:
        local_path = Path(tmp_file.name)

    try:
        response = client.download_file(remote_path, local_path)
        assert response.status_code == 200
        assert local_path.read_text() == "Test file content"
    finally:
        local_path.unlink(missing_ok=True)


def test_list_files(client: YandexDiskClient, test_file: Path, remote_test_folder: Path) -> None:
    test_files = [remote_test_folder / f"list_file_{i}.txt" for i in range(2)]
    for file in test_files:
        client.upload_file(test_file, file)

    _, files = client.list_files(remote_test_folder)
    assert files is not None
    assert len(files) >= 2
    assert all(f"list_file_{i}.txt" in [f["name"] for f in files] for i in range(2))


def test_path_operations(client: YandexDiskClient, remote_test_folder: Path) -> None:
    test_path = remote_test_folder / "test/sub/folder"

    assert not client._path_exists(test_path)
    assert client._ensure_path_exists(test_path)
    assert client._path_exists(test_path)


if __name__ == "__main__":
    pytest.main()
