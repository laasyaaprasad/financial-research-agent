"""Unit tests must not access any remote service."""

import socket

import pytest


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Network access is forbidden in unit tests")
    monkeypatch.setattr(socket.socket, "connect", blocked)
