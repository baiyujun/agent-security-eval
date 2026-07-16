"""Send one JSON request from the default Sandbox service to the Fake Target."""

from __future__ import annotations

import http.client
import json
import sys
from typing import Any, cast


def _request_from_stdin() -> dict[str, Any]:
    request = json.load(sys.stdin)
    if not isinstance(request, dict):
        raise ValueError("request must be a JSON object")
    return cast(dict[str, Any], request)


def main() -> None:
    request = _request_from_stdin()
    method = request.get("method")
    path = request.get("path")
    payload = request.get("payload")
    timeout = request.get("timeout")
    if not isinstance(method, str) or not isinstance(path, str):
        raise ValueError("method and path must be strings")
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    if not isinstance(timeout, int) or timeout <= 0:
        raise ValueError("timeout must be a positive integer")

    connection = http.client.HTTPConnection("target", 8080, timeout=timeout)
    try:
        connection.request(
            method,
            path,
            body=json.dumps(payload, sort_keys=True),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        body = response.read().decode("utf-8")
    finally:
        connection.close()

    if response.status >= 400:
        raise RuntimeError(f"target returned HTTP {response.status}: {body}")
    decoded = json.loads(body)
    if not isinstance(decoded, dict):
        raise ValueError("target response must be a JSON object")
    json.dump(decoded, sys.stdout, sort_keys=True, separators=(",", ":"))


if __name__ == "__main__":
    main()
