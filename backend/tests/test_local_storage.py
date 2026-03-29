"""Local filesystem storage backend."""

from __future__ import annotations

import sys

import pytest

from app.services.storage_service import LocalStorageService, _safe_local_object_path


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX absolute path key")
def test_safe_local_path_rejects_absolute_key(tmp_path):
    root = tmp_path / "store"
    root.mkdir()
    with pytest.raises(ValueError, match="path traversal"):
        _safe_local_object_path(str(root), "/etc/passwd")


def test_local_storage_roundtrip(tmp_path):
    svc = LocalStorageService(str(tmp_path))
    src = tmp_path / "source.txt"
    src.write_text("hello-local-storage", encoding="utf-8")
    key = "users/u1/documents/ab12/file.txt"
    svc.upload_file(str(src), key)

    dest = tmp_path / "out.txt"
    svc.download_file(key, str(dest))
    assert dest.read_text(encoding="utf-8") == "hello-local-storage"

    svc.delete_file(key)
    stored = tmp_path / "users" / "u1" / "documents" / "ab12" / "file.txt"
    assert not stored.exists()


def test_local_absolute_path(tmp_path):
    svc = LocalStorageService(str(tmp_path))
    p = svc.absolute_path("a/b/c.pdf")
    assert p.resolve().is_relative_to(tmp_path.resolve())
