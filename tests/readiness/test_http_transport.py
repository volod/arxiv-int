"""Network-free coverage of bounded production HTTP transport."""

import socket
from http.client import HTTPException
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from arxiv_int.readiness import LocalProbe
from arxiv_int.readiness import http_transport as transport


@pytest.fixture
def connection(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    response = MagicMock(status=200)
    response.read.return_value = b'{"models": []}'
    response.__enter__.return_value = response
    connection = MagicMock()
    connection.getresponse.return_value = response
    monkeypatch.setattr(transport, "HTTPConnection", MagicMock(return_value=connection))
    monkeypatch.setattr(transport, "HTTPSConnection", MagicMock(return_value=connection))
    return connection


def test_json_and_nondefault_port(connection: MagicMock) -> None:
    result = LocalProbe().get_json("http://localhost:8100/v1/models", timeout=1)
    assert result.status == 200
    assert result.payload == {"models": []}
    transport.HTTPConnection.assert_called_once_with("127.0.0.1", 8100, timeout=1)
    connection.getresponse.return_value.read.assert_called_once_with(
        transport.MAX_RESPONSE_BYTES + 1
    )
    connection.close.assert_called_once()


@pytest.mark.parametrize(
    "url",
    [
        "http://user:fixture-secret@localhost/",
        "http://example.com/",
        "http://[broken/",
        "http://localhost:bad/",
        "http://localhost:0/",
        "ftp://localhost/",
        "http://localhost/?token=fixture-secret",
        "http://localhost/#fragment",
        "http://local\nhost/",
    ],
)
def test_invalid_url_never_connects(connection: MagicMock, url: str) -> None:
    result = LocalProbe().get_json(url, timeout=1)
    assert result.status is None
    assert result.error == "ValueError"
    connection.connect.assert_not_called()


@pytest.mark.parametrize("status", [301, 302, 307, 308, 401, 503])
def test_redirects_and_http_errors_are_not_followed(connection: MagicMock, status: int) -> None:
    response = connection.getresponse.return_value
    response.status = status
    response.headers = {"Location": "https://fixture-secret@example.com/"}
    result = LocalProbe().get_json("http://127.0.0.1/", timeout=1)
    assert result.error == f"HTTP {status}"
    connection.request.assert_called_once()
    response.read.assert_not_called()


@pytest.mark.parametrize(
    "body", [b"", b"not json", b'"\xff"', b"[" * 2000, b" " * (transport.MAX_RESPONSE_BYTES + 1)]
)
def test_malformed_and_oversized_bodies_fail_safely(connection: MagicMock, body: bytes) -> None:
    connection.getresponse.return_value.read.return_value = body
    result = LocalProbe().get_json("http://127.0.0.1/", timeout=1)
    assert result.status is None
    assert result.error
    connection.close.assert_called_once()


@pytest.mark.parametrize("error", [OSError, TimeoutError, HTTPException, ValueError])
def test_errors_do_not_echo_transport_details(
    connection: MagicMock, error: type[Exception]
) -> None:
    connection.getresponse.side_effect = error("fixture-secret")
    result = LocalProbe().get_json("http://127.0.0.1/", timeout=1)
    assert result.error == error.__name__
    connection.close.assert_called_once()


def test_deadline_interrupts_socket_and_cleans_timer(
    connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    timer = MagicMock()
    factory = MagicMock(return_value=timer)
    monkeypatch.setattr(transport, "Timer", factory)
    monkeypatch.setattr(transport, "monotonic", MagicMock(side_effect=[0, 0.25, 1.1]))
    result = LocalProbe().get_json("http://127.0.0.1/", timeout=1)
    assert result.error == "TimeoutError"
    delay, callback, args = factory.call_args.args
    assert delay == 0.75
    callback(*args)
    connection.sock.shutdown.assert_called_once_with(socket.SHUT_RDWR)
    timer.cancel.assert_called_once()
    timer.join.assert_called_once()


def test_closed_socket_deadline_is_harmless() -> None:
    stream = SimpleNamespace(shutdown=MagicMock(side_effect=OSError))
    transport._shutdown(stream)


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf")])
def test_invalid_timeout_never_connects(connection: MagicMock, timeout: float) -> None:
    assert LocalProbe().get_json("http://localhost/", timeout=timeout).error == "ValueError"
    connection.connect.assert_not_called()


def test_ipv6_https_uses_direct_connection(connection: MagicMock) -> None:
    assert LocalProbe().get_json("https://[::1]:8443/", timeout=1).status == 200
    transport.HTTPSConnection.assert_called_once_with("::1", 8443, timeout=1)


def test_connect_exhausting_deadline_closes_connection(
    connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(transport, "monotonic", MagicMock(side_effect=[0, 2]))
    assert LocalProbe().get_json("http://localhost/", timeout=1).error == "TimeoutError"
    connection.request.assert_not_called()
    connection.close.assert_called_once()
