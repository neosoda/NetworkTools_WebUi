import asyncio

from pydantic import ValidationError
from fastapi import HTTPException
import pytest

from server.api.ssh_cmd import StartSSHRequest, stop_ssh


def test_start_ssh_request_rejects_invalid_ip() -> None:
    with pytest.raises(ValidationError):
        StartSSHRequest(ips=["999.999.1.1"], commands=["show version"])


def test_start_ssh_request_rejects_empty_commands() -> None:
    with pytest.raises(ValidationError):
        StartSSHRequest(ips=["192.168.1.1"], commands=["   "])


def test_stop_ssh_raises_404_when_missing() -> None:
    with pytest.raises(HTTPException) as exc:
        asyncio.run(stop_ssh("missing-task"))
    assert exc.value.status_code == 404
