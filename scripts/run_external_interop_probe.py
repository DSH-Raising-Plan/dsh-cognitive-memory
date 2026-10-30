# -*- coding: utf-8 -*-
"""Boot a local Mnemosyne node and run the external weather adapter probe."""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "examples" / "external-weather-adapter" / "external_weather_adapter.py"
TOKEN = "probe-token-external"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_health(base: str, timeout: float = 25.0) -> None:
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        try:
            req = urllib.request.Request(
                f"{base}/api/v1/health",
                headers={"Authorization": f"Bearer {TOKEN}"},
            )
            with urllib.request.urlopen(req, timeout=2) as res:
                if res.status == 200:
                    return
        except Exception as exc:  # noqa: BLE001
            last = str(exc)
            time.sleep(0.25)
    raise RuntimeError(f"service not healthy: {last}")


def main() -> int:
    port = _free_port()
    data = tempfile.mkdtemp(prefix="mnemosyne-probe-")
    env = os.environ.copy()
    env["DSH_MEMORY_TOKEN"] = TOKEN
    env["PYTHONPATH"] = str(ROOT / "service" / "src") + os.pathsep + env.get(
        "PYTHONPATH", ""
    )
    boot = (
        "from mnemosyne.bootstrap import build_context\n"
        "import uvicorn\n"
        f"ctx = build_context(data_dir={data!r}, token={TOKEN!r}, "
        "acquire_lock=False, auto_backup_on_migrate=False, "
        f"host='127.0.0.1', port={port})\n"
        f"uvicorn.run(ctx.app, host='127.0.0.1', port={port}, log_level='warning')\n"
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", boot],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        try:
            _wait_health(base)
        except RuntimeError:
            out = ""
            try:
                proc.kill()
                out = proc.communicate(timeout=3)[0] or ""
            except Exception:
                pass
            print(out[-3000:], file=sys.stderr)
            raise
        return subprocess.call(
            [sys.executable, str(ADAPTER), base, TOKEN],
            cwd=str(ROOT),
        )
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
