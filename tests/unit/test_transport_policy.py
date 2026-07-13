from __future__ import annotations

import socket

import pytest

from apmatia.core.security.transport import is_loopback_bind


def _addrinfo(address: str) -> tuple:
    if ":" in address:
        return (socket.AF_INET6, socket.SOCK_STREAM, 6, "", (address, 0, 0, 0))
    return (socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 0))


@pytest.mark.parametrize(
    "host",
    [
        "127.0.0.1",
        "127.0.0.2",
        "::1",
    ],
)
def test_direct_loopback_addresses_are_loopback(host):
    assert is_loopback_bind(host) is True


@pytest.mark.parametrize(
    "host",
    [
        "0.0.0.0",
        "::",
        "192.168.86.10",
        "10.0.0.4",
        "2001:db8::1",
        "8.8.8.8",
    ],
)
def test_non_loopback_addresses_are_not_loopback(host):
    assert is_loopback_bind(host) is False


def test_localhost_is_loopback_only_when_all_resolved_addresses_are_loopback(monkeypatch):
    def fake_getaddrinfo(host, *_args, **_kwargs):
        assert host == "localhost"
        return [
            _addrinfo("127.0.0.1"),
            _addrinfo("::1"),
        ]

    monkeypatch.setattr("apmatia.core.security.transport.socket.getaddrinfo", fake_getaddrinfo)

    assert is_loopback_bind("localhost") is True


def test_hostname_with_any_non_loopback_address_is_not_loopback_only(monkeypatch):
    def fake_getaddrinfo(host, *_args, **_kwargs):
        assert host == "mixed.example"
        return [
            _addrinfo("127.0.0.1"),
            _addrinfo("192.168.86.10"),
        ]

    monkeypatch.setattr("apmatia.core.security.transport.socket.getaddrinfo", fake_getaddrinfo)

    assert is_loopback_bind("mixed.example") is False


def test_resolution_failure_is_not_treated_as_loopback(monkeypatch):
    def fake_getaddrinfo(*_args, **_kwargs):
        raise socket.gaierror("name resolution failed")

    monkeypatch.setattr("apmatia.core.security.transport.socket.getaddrinfo", fake_getaddrinfo)

    assert is_loopback_bind("missing.example") is False
