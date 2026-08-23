"""Start the real Streamlit server and require a successful HTTP response."""

import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from ai_growth_companion.repositories.database import Database, run_migrations


def free_port() -> int:
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        return int(candidate.getsockname()[1])


def main() -> None:
    port = free_port()
    with tempfile.TemporaryDirectory(prefix="agc-smoke-") as temporary_directory:
        database_path = Path(temporary_directory) / "smoke.db"
        database_url = f"sqlite:///{database_path.as_posix()}"
        run_migrations(Database(database_url))

        environment = os.environ.copy()
        environment.update(
            {
                "DATABASE_URL": database_url,
                "LLM_PROVIDER": "fake",
                "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
            }
        )
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "app.py",
                "--server.headless=true",
                "--server.address=127.0.0.1",
                f"--server.port={port}",
            ],
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    output = process.stdout.read() if process.stdout else ""
                    raise RuntimeError(f"Streamlit exited before readiness:\n{output}")
                try:
                    with urllib.request.urlopen(  # noqa: S310 - fixed localhost URL
                        f"http://127.0.0.1:{port}", timeout=1
                    ) as response:
                        content = response.read().decode("utf-8", errors="replace")
                        if response.status == 200 and "streamlit" in content.lower():
                            print(f"Streamlit smoke test passed on port {port}")
                            return
                except OSError:
                    time.sleep(0.25)
            raise RuntimeError("Streamlit did not become ready within 20 seconds")
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
