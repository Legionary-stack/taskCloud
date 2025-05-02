import time
import zipfile
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Generator

import pytest
import requests

from src.client.google_drive_client import GoogleDriveClient


@pytest.fixture(scope="module")
def client() -> Generator[GoogleDriveClient, None, None]:
    client = GoogleDriveClient()

    if client.check_disk_access().status_code != 200:
        pytest.skip("Google Drive недоступен (проверьте токен и подключение)")

    yield client


@pytest.fixture
def test_file() -> Generator[Path, None, None]:
    with NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("Test file content")
        file_path = Path(f.name)

    yield file_path
    file_path.unlink(missing_ok=True)


@pytest.fixture
def test_zip_file(test_file: Path) -> Generator[Path, None, None]:
    zip_path = test_file.with_suffix('.zip')
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        zipf.write(test_file, arcname=test_file.name)

    yield zip_path
    zip_path.unlink(missing_ok=True)


@pytest.fixture
def test_folder() -> Generator[Path, None, None]:
    with TemporaryDirectory() as temp_dir:
        dir_path = Path(temp_dir)
        for i in range(3):
            (dir_path / f"file_{i}.txt").write_text(f"Content {i}")
        yield dir_path


@pytest.fixture
def remote_test_folder(client: GoogleDriveClient) -> Generator[str, None, None]:
    folder_name = "pytest_test_folder"
    folder_id = client._ensure_path_exists(Path(folder_name))

    yield folder_name

    try:
        requests.delete(
            f"{client._settings.base_url}/files/{folder_id}",
            headers={"Authorization": f"Bearer {client._settings.access_token}"},
        )
    except Exception as e:
        print(f"Ошибка очистки тестовой папки: {e}")


def test_upload_file(client: GoogleDriveClient, test_file: Path, remote_test_folder: str) -> None:
    remote_path = Path(f"{remote_test_folder}/test_file.zip")

    response = client.upload_file(test_file, remote_path)
    assert response.status_code == 200

    result = client.list_files(Path(remote_test_folder))
    assert result.files is not None
    assert any(item["name"] == "test_file.zip" for item in result.files)


def test_upload_zip_file(client: GoogleDriveClient, test_zip_file: Path, remote_test_folder: str) -> None:
    remote_path = Path(f"{remote_test_folder}/uploaded_zip.zip")

    response = client.upload_file(test_zip_file, remote_path)
    assert response.status_code == 200

    result = client.list_files(Path(remote_test_folder))
    assert result.files is not None
    assert any(item["name"] == "uploaded_zip.zip" for item in result.files)


def test_upload_folder(client: GoogleDriveClient, test_folder: Path, remote_test_folder: str) -> None:
    remote_path = Path(f"{remote_test_folder}/test_folder")

    responses = client.upload_folder(test_folder, remote_path)
    assert all(r.status_code == 200 for r in responses)

    result = client.list_files(remote_path)
    assert result.files is not None
    assert len(result.files) == 3


def test_download_file(client: GoogleDriveClient, test_file: Path, remote_test_folder: str) -> None:
    remote_path = Path(f"{remote_test_folder}/download_test.zip")
    client.upload_file(test_file, remote_path)
    time.sleep(1)

    with NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
        local_zip_path = Path(tmp_file.name)

    try:
        response = client.download_file(remote_path, local_zip_path)
        assert response.status_code == 200

        with zipfile.ZipFile(local_zip_path, 'r') as zipf:
            with zipf.open(test_file.name) as extracted_file:
                content = extracted_file.read().decode('utf-8')
                assert content == "Test file content"
    finally:
        local_zip_path.unlink(missing_ok=True)


def test_list_files(client: GoogleDriveClient, test_file: Path, remote_test_folder: str) -> None:
    test_files = [Path(f"{remote_test_folder}/list_file_{i}.zip") for i in range(2)]
    for file in test_files:
        client.upload_file(test_file, file)
    time.sleep(1)

    result = client.list_files(Path(remote_test_folder))
    assert result.files is not None
    assert len(result.files) >= 2
    assert all(f"list_file_{i}.zip" in [f["name"] for f in result.files] for i in range(2))


def test_path_operations(client: GoogleDriveClient, remote_test_folder: str) -> None:
    test_path = Path(f"{remote_test_folder}/test/sub/folder")

    assert not client._path_exists(test_path)
    assert client._ensure_path_exists(test_path)
    assert client._path_exists(test_path)


if __name__ == "__main__":
    pytest.main()
