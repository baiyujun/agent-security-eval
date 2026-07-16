"""Deterministic standard-library HTTP Target used only by the M0-A Docker fixture."""

from __future__ import annotations

import json
import threading
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar, cast
from urllib.parse import urlparse

EFFECTS_DIRECTORY = Path("/effects")


class TargetHandler(BaseHTTPRequestHandler):
    sessions: ClassVar[dict[str, dict[str, Any]]] = {}
    sessions_lock: ClassVar[threading.Lock] = threading.Lock()

    def do_GET(self) -> None:
        parts = self._path_parts()
        if parts == ["health"]:
            self._send_json(HTTPStatus.OK, {"status": "ready"})
            return
        if len(parts) == 2 and parts[0] == "sessions":
            self._get_session(parts[1])
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "unknown endpoint"})

    def do_POST(self) -> None:
        parts = self._path_parts()
        try:
            payload = self._read_json_object()
            if parts == ["sessions"]:
                self._open_session(payload)
                return
            if len(parts) == 3 and parts[0] == "sessions" and parts[2] == "turns":
                self._send_turn(parts[1], payload)
                return
            if len(parts) == 3 and parts[0] == "sessions" and parts[2] == "close":
                self._close_session(parts[1])
                return
        except ValueError as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "unknown endpoint"})

    def _open_session(self, payload: dict[str, Any]) -> None:
        run_id = self._required_string(payload, "run_id")
        canary = self._required_string(payload, "canary")
        session_id = f"session-{uuid.uuid5(uuid.NAMESPACE_URL, run_id).hex}"
        session: dict[str, Any] = {
            "run_id": run_id,
            "session_id": session_id,
            "canary": canary,
            "turn": 0,
            "closed": False,
            "effect_path": None,
        }
        with self.sessions_lock:
            self.sessions[session_id] = session
        self._send_json(HTTPStatus.CREATED, {"session_id": session_id})

    def _send_turn(self, session_id: str, payload: dict[str, Any]) -> None:
        message = self._required_string(payload, "message")
        with self.sessions_lock:
            session = self.sessions.get(session_id)
            if session is None:
                raise ValueError("unknown session")
            if session["closed"]:
                raise ValueError("session is closed")
            session["turn"] = cast(int, session["turn"]) + 1
            turn = cast(int, session["turn"])
            run_id = cast(str, session["run_id"])
            canary = cast(str, session["canary"])

        response: dict[str, Any] = {
            "session_id": session_id,
            "turn": turn,
            "response": f"accepted:{message}",
            "tool_calls": [],
            "effect_path": None,
        }
        if turn == 2:
            response["tool_calls"] = [
                {
                    "call_id": f"tool-{session_id}-2",
                    "name": "read_file",
                    "arguments": {"path": "/fixture/public.txt"},
                    "result": {"content": "deterministic public fixture"},
                }
            ]
        elif turn == 3:
            effect_path = str(EFFECTS_DIRECTORY / f"{session_id}.json")
            Path(effect_path).write_text(
                json.dumps(
                    {"run_id": run_id, "session_id": session_id, "canary": canary},
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            with self.sessions_lock:
                self.sessions[session_id]["effect_path"] = effect_path
            response["effect_path"] = effect_path
            response["response"] = "environment effect written"
        self._send_json(HTTPStatus.OK, response)

    def _get_session(self, session_id: str) -> None:
        with self.sessions_lock:
            session = self.sessions.get(session_id)
            snapshot = dict(session) if session is not None else None
        if snapshot is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "unknown session"})
            return
        self._send_json(HTTPStatus.OK, snapshot)

    def _close_session(self, session_id: str) -> None:
        with self.sessions_lock:
            session = self.sessions.get(session_id)
            if session is None:
                raise ValueError("unknown session")
            session["closed"] = True
        self._send_json(HTTPStatus.OK, {"session_id": session_id, "closed": True})

    def _read_json_object(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        decoded = json.loads(self.rfile.read(content_length) or b"{}")
        if not isinstance(decoded, dict):
            raise ValueError("request body must be a JSON object")
        return cast(dict[str, Any], decoded)

    def _path_parts(self) -> list[str]:
        return [part for part in urlparse(self.path).path.split("/") if part]

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _required_string(payload: dict[str, Any], field: str) -> str:
        value = payload.get(field)
        if not isinstance(value, str) or not value:
            raise ValueError(f"{field} must be a non-empty string")
        return value

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    EFFECTS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("0.0.0.0", 8080), TargetHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
