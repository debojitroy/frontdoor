"""Isolated, disposable database for browser tests; never touches a user's workbench."""

import tempfile
from pathlib import Path

import uvicorn
from frontdoor.main import create_app

if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="frontdoor-e2e-") as directory:
        uvicorn.run(
            create_app(Path(directory) / "test.db", live_enabled=False),
            host="127.0.0.1",
            port=8143,
            log_level="warning",
        )
