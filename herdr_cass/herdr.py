"""Minimal client for herdr's newline-delimited JSON socket API."""

import json
import os
import socket
from pathlib import Path

HERDR_HOME = Path.home() / ".config" / "herdr"
DEFAULT_SESSION = "default"


class HerdrError(Exception):
    def __init__(self, code, message):
        super().__init__(f"{code}: {message}")
        self.code = code


class Client:
    def __init__(self, socket_path=None, timeout=15):
        self.socket_path = str(
            socket_path or os.environ.get("HERDR_SOCKET_PATH") or HERDR_HOME / "herdr.sock"
        )
        self.timeout = timeout

    def call(self, method, params=None):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(self.timeout)
            sock.connect(self.socket_path)
            request = {"id": f"herdr-cass:{method}", "method": method, "params": params or {}}
            sock.sendall((json.dumps(request) + "\n").encode())
            buf = b""
            while b"\n" not in buf:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                buf += chunk
        reply = json.loads(buf.split(b"\n", 1)[0])
        if "error" in reply:
            raise HerdrError(reply["error"].get("code"), reply["error"].get("message"))
        return reply.get("result", {})

    def tab_create(self, workspace_id, cwd, label=None):
        params = {"workspace_id": workspace_id, "cwd": cwd, "focus": True}
        if label:
            params["label"] = label
        return self.call("tab.create", params)

    def pane_send_input(self, pane_id, text, keys=("Enter",)):
        self.call("pane.send_input", {"pane_id": pane_id, "text": text, "keys": list(keys)})

    def notify(self, title, body=None):
        try:
            self.call("notification.show", {"title": title, "body": body})
        except (OSError, HerdrError):
            pass

    def plugin_pane_open(self, plugin_id, entrypoint, env=None):
        self.call(
            "plugin.pane.open",
            {"plugin_id": plugin_id, "entrypoint": entrypoint, "focus": True, "env": env or {}},
        )
