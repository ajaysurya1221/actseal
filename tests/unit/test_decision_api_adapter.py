"""Decision-API transport checks use mocked connections, never a live server."""

from __future__ import annotations

import http.client
import json
import os

import pytest
from test_jev import MOCK_KEY, FakeConnect, FakeConnection, Script

from actseal.errors import ProviderSetupError
from actseal.experimental.providers import jev
from actseal.experimental.providers.decision_api import DecisionAPIModel
from conftest import make_request


def test_configurable_model_is_sent_without_altering_question_order() -> None:
    body = jev.request_body(make_request(), model="local-choice-v2")
    payload = json.loads(body)
    assert payload["model"] == "local-choice-v2"
    assert list(payload) == ["state", "model", "questions"]
    assert list(payload["questions"]["department"]["criteria"]) == [
        "billing",
        "technical",
        "sales",
    ]


def test_shared_exchange_allows_absent_credentials_and_custom_path() -> None:
    connect = FakeConnect(Script(body=b'{"body":"retained"}'))
    exchange = jev._HttpsExchange(None, connect, path="/decide", warning_prefix="decision-api")
    reply = exchange(b"{}", 2.0)
    assert reply.body == '{"body":"retained"}'
    assert reply.failure is None
    assert connect.log[0].url == "/decide"
    assert "Authorization" not in connect.log[0].headers


@pytest.mark.parametrize(
    ("status", "expected"),
    [(301, "provider_error"), (401, "provider_error"), (429, "rate_limit"), (529, "unavailable")],
)
def test_shared_exchange_maps_status_without_retry_or_retaining_error_body(
    status: int, expected: str
) -> None:
    connect = FakeConnect(Script(status=status, body=b"error text"))
    exchange = jev._HttpsExchange(None, connect, warning_prefix="decision-api")
    reply = exchange(b"{}", 2.0)
    assert reply.failure == expected
    assert reply.body is None
    assert reply.warnings == (f"decision-api.http:{status}",)
    assert len(connect.log) == 1
    assert connect.log[0].delivered == 0
    assert connect.log[0].closed == 1


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://example.com/decide",
        "http://127.1/decide",
        "http://localhost.evil/decide",
        "http://localhost./decide",
        "http://[::ffff:127.0.0.1]/decide",
        "http://[::1]evil/decide",
        "https://[::1]evil/decide",
        "https://[::1%eth0]/decide",
        "ftp://localhost/decide",
        "https:///decide",
        "https://user:password@example.com/decide",
        "https://example.com/decide#fragment",
        "https://example.com/decide?api_key=value",
        "https://example.com:0/decide",
        "https://example.com:65536/decide",
        "https://example.com:/decide",
        "https://example.com:not-a-port/decide",
        " https://example.com/decide",
        "https://example.com/decide\n",
        "https://example.com\\other/decide",
        "https://%6cocalhost/decide",
    ],
)
def test_invalid_endpoints_are_rejected_without_echo_or_environment_read(
    endpoint: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_environment(_name: str, _default: str | None = None) -> str | None:
        raise AssertionError("environment read before validating endpoint")

    monkeypatch.setattr(os.environ, "get", no_environment)
    with pytest.raises(ProviderSetupError, match="endpoint:") as caught:
        DecisionAPIModel(endpoint=endpoint, model="local-v2", revision="r1")
    assert endpoint not in str(caught.value)


@pytest.mark.parametrize(
    ("endpoint", "connection_type", "host", "port", "path"),
    [
        ("http://localhost:8080/decide", "HTTPConnection", "localhost", 8080, "/decide"),
        ("http://127.0.0.1/decide", "HTTPConnection", "127.0.0.1", None, "/decide"),
        ("http://[::1]:8081/decide", "HTTPConnection", "::1", 8081, "/decide"),
        ("https://example.com:8443/v1", "HTTPSConnection", "example.com", 8443, "/v1"),
        ("https://example.com", "HTTPSConnection", "example.com", None, "/"),
    ],
)
def test_configured_endpoint_identity_and_one_attempt_without_credentials(
    *,
    endpoint: str,
    connection_type: str,
    host: str,
    port: int | None,
    path: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connect = FakeConnect(Script(body=b' {"any":"body"} '))

    def connection(
        actual_host: str, actual_port: int | None, *, timeout: float, **kwargs: object
    ) -> FakeConnection:
        assert actual_host == host
        assert actual_port == port
        assert ("context" in kwargs) == (connection_type == "HTTPSConnection")
        return connect(timeout)

    monkeypatch.setattr(http.client, connection_type, connection)
    model = DecisionAPIModel(endpoint=endpoint, model="local-v2", revision="r1")
    identity = model.identity()
    assert identity.provider == "decision-api"
    assert identity.model == "local-v2"
    assert identity.revision == "r1"
    assert dict(identity.runtime)["endpoint"] == endpoint
    capture = model.decide(make_request(), timeout_s=3.5)
    assert capture.body_json == ' {"any":"body"} '
    assert capture.identity == identity
    assert len(connect.log) == 1
    assert connect.log[0].url == path
    assert connect.log[0].timeout == 3.5
    assert "Authorization" not in connect.log[0].headers
    assert json.loads(connect.log[0].body)["model"] == "local-v2"
    assert connect.log[0].closed == 1
    model.close()
    model.close()
    assert model.decide(make_request(), timeout_s=3.5).failure_code == "unavailable"
    assert len(connect.log) == 1


@pytest.mark.parametrize("value", [None, "", "bad key", "bad\nkey", "é", "x" * 4097])
def test_explicit_key_environment_requires_a_valid_token(
    value: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    if value is None:
        monkeypatch.delenv("ACTSEAL_TEST_KEY", raising=False)
    else:
        monkeypatch.setenv("ACTSEAL_TEST_KEY", value)
    with pytest.raises(ProviderSetupError, match="ACTSEAL_TEST_KEY:"):
        DecisionAPIModel(
            endpoint="https://example.com/v1",
            model="local-v2",
            revision="r1",
            api_key_env="ACTSEAL_TEST_KEY",
        )


@pytest.mark.parametrize("name", ["", "A=B", "1KEY", "BAD KEY", "KEY\n", "é"])
def test_invalid_key_environment_names_are_rejected(name: str) -> None:
    with pytest.raises(ProviderSetupError, match="api_key_env:"):
        DecisionAPIModel(
            endpoint="http://localhost/v1", model="local-v2", revision="r1", api_key_env=name
        )


@pytest.mark.parametrize("escaped", [False, True])
def test_optional_credentials_are_sent_but_never_captured(
    escaped: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = "".join(f"\\u{ord(char):04x}" for char in MOCK_KEY) if escaped else MOCK_KEY
    connect = FakeConnect(Script(body=body.encode()))

    def connection(
        _host: str, _port: int | None, *, timeout: float, **_kwargs: object
    ) -> FakeConnection:
        return connect(timeout)

    monkeypatch.setattr(http.client, "HTTPConnection", connection)
    monkeypatch.setenv("ACTSEAL_TEST_KEY", MOCK_KEY)
    model = DecisionAPIModel(
        endpoint="http://localhost/v1",
        model="local-v2",
        revision="r1",
        api_key_env="ACTSEAL_TEST_KEY",
    )
    capture = model.decide(make_request(), timeout_s=2.0)
    assert connect.log[0].headers["Authorization"] == f"Bearer {MOCK_KEY}"
    assert capture.failure_code == "malformed_response"
    assert capture.body_json is None
    assert capture.warnings == ("decision-api.credential_echo",)
    assert MOCK_KEY not in repr(capture)


def test_offline_rejected_before_environment_access(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_environment(_name: str, _default: str | None = None) -> str | None:
        raise AssertionError("offline setup read the environment")

    monkeypatch.setattr(os.environ, "get", no_environment)
    with pytest.raises(ProviderSetupError, match="offline:"):
        DecisionAPIModel(
            endpoint="http://localhost/v1",
            model="local-v2",
            revision="r1",
            api_key_env="ACTSEAL_TEST_KEY",
            offline=True,
        )


@pytest.mark.parametrize(("model", "revision"), [("", "r1"), ("local-v2", "")])
def test_model_and_revision_are_required(model: str, revision: str) -> None:
    with pytest.raises(ProviderSetupError):
        DecisionAPIModel(endpoint="http://localhost/v1", model=model, revision=revision)


@pytest.mark.parametrize(
    ("script", "failure"),
    [
        (Script(body=b"\xff"), "malformed_response"),
        (Script(body=b"x" * (jev.MAX_RESPONSE_BYTES + 20)), "malformed_response"),
        (Script(body=b"short", length=20), "unavailable"),
        (Script(raise_on_read=TimeoutError()), "timeout"),
        (Script(raise_on_request=OSError()), "unavailable"),
        (Script(raise_on_response=ValueError()), "provider_error"),
    ],
)
def test_configured_transport_preserves_jev_body_limits_and_failures(
    script: Script, failure: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    connect = FakeConnect(script)

    def connection(
        _host: str, _port: int | None, *, timeout: float, **_kwargs: object
    ) -> FakeConnection:
        return connect(timeout)

    monkeypatch.setattr(http.client, "HTTPConnection", connection)
    model = DecisionAPIModel(endpoint="http://localhost/v1", model="local-v2", revision="r1")
    capture = model.decide(make_request(), timeout_s=2.0)
    assert capture.failure_code == failure
    assert capture.body_json is None
    assert len(connect.log) == 1
    assert connect.log[0].delivered <= jev.MAX_RESPONSE_BYTES + 1
    assert connect.log[0].closed == 1
