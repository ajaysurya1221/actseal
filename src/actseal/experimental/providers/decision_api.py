"""PROVISIONAL configurable Jev-compatible transport, sharing Jev's capture rules.

Endpoint URLs use HTTPS, or HTTP only at the literal loopback hosts localhost,
127.0.0.1 and ::1. User information, query strings and fragments are rejected:
credentials belong only in the optional named environment variable. Endpoint,
model and user-supplied revision are locked identity, not weight attestations.
Importing this module performs no environment access or network calls.
"""

from __future__ import annotations

import http.client
import ipaddress
import platform
import re
import ssl
from dataclasses import dataclass
from typing import Final
from urllib.parse import urlsplit

from actseal.errors import ProviderSetupError, SchemaError
from actseal.experimental.providers.jev import (
    ADAPTER_VERSION,
    _api_key_from_environment,
    _Connection,
    _DecisionModel,
    _HttpsExchange,
)
from actseal.normalization import NORMALIZER_VERSION
from actseal.records import ModelIdentity

__all__ = ["DecisionAPIModel"]

_LOOPBACK: Final = frozenset({"localhost", "127.0.0.1", "::1"})
_ENV_NAME: Final = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_HOST: Final = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\Z")


@dataclass(frozen=True, slots=True)
class _Endpoint:
    scheme: str
    host: str
    port: int | None
    path: str

    def connect(self, timeout: float) -> _Connection:
        if self.scheme == "https":
            return http.client.HTTPSConnection(
                self.host, self.port, timeout=timeout, context=ssl.create_default_context()
            )
        return http.client.HTTPConnection(self.host, self.port, timeout=timeout)


def _endpoint(value: object) -> _Endpoint:
    error = (
        "endpoint: expected HTTPS or literal-loopback HTTP without credentials, query or fragment"
    )
    if (
        not isinstance(value, str)
        or not value.isascii()
        or not value.isprintable()
        or any(char.isspace() for char in value)
        or any(char in value for char in "\\?#")
    ):
        raise ProviderSetupError(error)
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        raise ProviderSetupError(error) from None
    if (
        parsed.scheme not in {"http", "https"}
        or not host
        or "%" in host
        or parsed.username is not None
        or parsed.password is not None
        or parsed.netloc.endswith(":")
        or port == 0
        or (parsed.scheme == "http" and host not in _LOOPBACK)
    ):
        raise ProviderSetupError(error)
    if ":" in host:
        try:
            ipaddress.IPv6Address(host)
        except ValueError:
            raise ProviderSetupError(error) from None
    elif _HOST.fullmatch(host) is None:
        raise ProviderSetupError(error)
    return _Endpoint(parsed.scheme, host, port, parsed.path or "/")


def _optional_api_key(name: object) -> str | None:
    if name is None:
        return None
    if not isinstance(name, str) or _ENV_NAME.fullmatch(name) is None:
        raise ProviderSetupError("api_key_env: must be an environment variable name")
    return _api_key_from_environment(name)


class DecisionAPIModel(_DecisionModel):
    """A locked endpoint/model/revision using the shared one-attempt Jev transport."""

    def __init__(
        self,
        *,
        endpoint: str,
        model: str,
        revision: str,
        api_key_env: str | None = None,
        offline: bool = False,
    ) -> None:
        if offline:
            raise ProviderSetupError(
                "offline: the experimental decision-api adapter has no offline mode; "
                "no request was made"
            )
        target = _endpoint(endpoint)
        try:
            identity = ModelIdentity(
                "decision-api",
                model,
                revision,
                (),
                ADAPTER_VERSION,
                NORMALIZER_VERSION,
                (
                    ("endpoint", endpoint),
                    ("execution_profile", "decision-api-single-attempt-v1"),
                    ("python", platform.python_version()),
                    (
                        "transport",
                        "stdlib-http.client-tls"
                        if target.scheme == "https"
                        else "stdlib-http.client",
                    ),
                    ("weights_attested", "false"),
                ),
            )
        except SchemaError as exc:
            raise ProviderSetupError(str(exc)) from None
        key = _optional_api_key(api_key_env)
        self._configure(
            _HttpsExchange(key, target.connect, path=target.path, warning_prefix="decision-api"),
            identity,
        )
