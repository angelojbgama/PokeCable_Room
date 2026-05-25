"""Battery M: LAN protocol loopback — server+client in same process, real socket."""
from __future__ import annotations

import socket
import sys
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent / "Pokecable_tool"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "pokecable_runtime"))

import importlib.util
_spec = importlib.util.spec_from_file_location("pokecable_lan", REPO_ROOT / "pokecable_lan.py")
_mod = importlib.util.module_from_spec(_spec)
sys.modules["pokecable_lan"] = _mod
_spec.loader.exec_module(_mod)
JsonLineConnection = _mod.JsonLineConnection

from tests._roundtrip.report import BatteryReport  # noqa: E402


def run() -> BatteryReport:
    report = BatteryReport(name="M: LAN loopback (JsonLineConnection)")

    # Bind on 127.0.0.1 with OS-assigned port
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("127.0.0.1", 0))
    port = server_sock.getsockname()[1]
    server_sock.listen(1)

    received_messages = []

    def server_thread():
        try:
            conn_sock, _ = server_sock.accept()
            conn = JsonLineConnection(conn_sock)
            # Receive a hello
            msg = conn.recv()
            received_messages.append(("server_got", msg))
            # Reply
            conn.send({"role": "server", "ack": True, "echo": msg})
            # Receive payload
            msg2 = conn.recv()
            received_messages.append(("server_got_payload", msg2))
            conn.send({"role": "server", "received_payload": True})
            conn.close()
        except Exception as exc:
            received_messages.append(("server_err", str(exc)))

    t = threading.Thread(target=server_thread, daemon=True)
    t.start()

    # Client
    try:
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_sock.connect(("127.0.0.1", port))
        client = JsonLineConnection(client_sock)
        client.send({"role": "client", "hello": "world"})
        reply = client.recv()
        if reply is None or not reply.get("ack"):
            report.add_fail(f"client got bad reply: {reply}")
        else:
            report.add_pass()
            report.note(f"hello/ack OK ({reply})")
        # Send a faux pokemon payload
        client.send({
            "payload_version": 2,
            "species_id": 6,
            "species_name": "Charizard",
            "level": 100,
            "metadata": {"gender": "♂"},
        })
        reply2 = client.recv()
        if reply2 is None or not reply2.get("received_payload"):
            report.add_fail(f"client got bad payload reply: {reply2}")
        else:
            report.add_pass()
            report.note(f"payload roundtrip OK ({reply2})")
        client.close()
    except Exception as exc:
        report.add_fail(f"client raised {type(exc).__name__}: {exc}")

    t.join(timeout=3.0)
    server_sock.close()

    # Verify server got the messages
    keys = {k for k, _ in received_messages}
    if "server_got" in keys and "server_got_payload" in keys:
        report.add_pass()
        report.note("server received both messages")
    else:
        report.add_fail(f"server didn't receive both: messages={received_messages}")

    return report
