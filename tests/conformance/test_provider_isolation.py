"""Import-time isolation: adapters load no transport, no worker and no native stack.

A fresh ``sys.executable -I`` child installs socket and process blockers
*before* importing the adapter modules, so an import-time connection or spawn
would raise. The child then proves the blockers are live (``LayaModel._spawn``
is refused), that no optional root entered ``sys.modules``, that the package
came from this checkout, and that a fixture ``decide`` needs neither.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from conftest import make_request
from provider_support import ROW_OK, independent_request_digest, write_rows

ACTSEAL_SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "actseal"
OPTIONAL_ROOTS = ("laya", "torch", "transformers", "huggingface_hub", "safetensors", "numpy")

CHILD = r"""
import json
import os
import socket
import subprocess
import sys


class Blocked(RuntimeError):
    pass


def block(*args, **kwargs):
    raise Blocked("blocked")


for name in ("socket", "create_connection", "socketpair", "getaddrinfo", "create_server"):
    setattr(socket, name, block)
subprocess.Popen = block
subprocess.run = block
os.system = block
for name in ("fork", "forkpty", "posix_spawn", "posix_spawnp", "execv", "execve",
             "execvp", "execvpe", "spawnv", "spawnve", "spawnvp", "spawnvpe"):
    if hasattr(os, name):
        setattr(os, name, block)

import actseal
import actseal.adapters
import actseal.adapters.base
import actseal.adapters.fixture
import actseal.adapters.laya
from pathlib import Path
from actseal.adapters.fixture import FixtureModel
from actseal.adapters.laya import LayaModel
from actseal.records import ChoiceQuestion, DecisionRequest, Option

roots = __ROOTS__
loaded = sorted({m.split(".")[0] for m in sys.modules if m.split(".")[0] in roots})

try:
    LayaModel._spawn(
        (sys.executable, "-c", "pass"), offline=True, startup_timeout_s=1.0, close_grace_s=0.1
    )
    spawn_blocked = False
except Blocked:
    spawn_blocked = True

try:
    socket.socket()
    socket_blocked = False
except Blocked:
    socket_blocked = True

model = FixtureModel(Path(sys.argv[1]))
question = ChoiceQuestion(
    "department",
    "Select the department responsible for this ticket.",
    (
        Option("billing", "Payments and refunds"),
        Option("technical", "Technical support"),
        Option("sales", "Purchasing questions"),
    ),
)
request = DecisionRequest("v-001", "Refund not received after cancellation.", question)
capture = model.decide(request, timeout_s=30.0)
model.close()
print(json.dumps({
    "actseal_file": actseal.__file__,
    "laya_file": actseal.adapters.laya.__file__,
    "fixture_file": actseal.adapters.fixture.__file__,
    "loaded": loaded,
    "spawn_blocked": spawn_blocked,
    "socket_blocked": socket_blocked,
    "request_sha256": capture.request_sha256,
    "body_json": capture.body_json,
    "failure_code": capture.failure_code,
    "provider": capture.identity.provider,
}))
print("provider-isolation-ok")
"""


def test_adapters_import_without_transport_worker_or_native_stack(tmp_path: Path) -> None:
    responses = tmp_path / "responses.jsonl"
    write_rows(responses, [ROW_OK])
    script = CHILD.replace("__ROOTS__", repr(OPTIONAL_ROOTS))
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal script, no user input
        [sys.executable, "-I", "-W", "error", "-c", script, str(responses)],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    lines = result.stdout.splitlines()
    assert lines[-1:] == ["provider-isolation-ok"], result.stdout[-2000:]
    report = json.loads(lines[-2])
    assert Path(report["actseal_file"]).resolve() == ACTSEAL_SOURCE_ROOT / "__init__.py"
    assert Path(report["laya_file"]).resolve() == ACTSEAL_SOURCE_ROOT / "adapters" / "laya.py"
    assert Path(report["fixture_file"]).resolve() == ACTSEAL_SOURCE_ROOT / "adapters" / "fixture.py"
    assert report["loaded"] == []
    assert report["spawn_blocked"] is True, "the process blocker must be live"
    assert report["socket_blocked"] is True, "the socket blocker must be live"
    assert report["provider"] == "fixture"
    assert report["failure_code"] is None
    assert report["body_json"] == ROW_OK["body_json"]
    assert report["request_sha256"] == independent_request_digest(make_request())
