import os
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.api.playbook import _resolve_playbook_path
from server.main import _safe_download_path


def test_safe_download_path_rejects_traversal() -> None:
    with pytest.raises(HTTPException):
        _safe_download_path("../secrets.txt")


def test_safe_download_path_accepts_plain_filename() -> None:
    resolved = _safe_download_path("report.txt")
    assert resolved.name == "report.txt"


def test_resolve_playbook_path_rejects_nested_paths() -> None:
    with pytest.raises(ValueError):
        _resolve_playbook_path("nested/playbook.yaml")


def test_resolve_playbook_path_accepts_filename_only() -> None:
    resolved = _resolve_playbook_path("baseline.yaml")
    assert resolved.name == "baseline.yaml"
    assert resolved.parent == Path("playbooks").resolve()
