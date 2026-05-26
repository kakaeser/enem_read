"""APILauncher: probes /health and auto-starts uvicorn when the desktop app opens."""

import asyncio
import subprocess
import time

import httpx


class APILauncher:
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8000,
        app_module: str = "backend.api.app:app",
        poll_interval: float = 0.5,
        timeout: float = 10.0,
    ) -> None:
        self._host = host
        self._port = port
        self._app_module = app_module
        self._poll_interval = poll_interval
        self._timeout = timeout
        self._process: subprocess.Popen | None = None

    @property
    def health_url(self) -> str:
        # Always probe via localhost regardless of bind host
        return f"http://127.0.0.1:{self._port}/health"

    async def start_if_needed(self) -> bool:
        """Probe /health; start uvicorn if unreachable.

        Returns True if this launcher started the server, False if it was
        already running.  Raises RuntimeError if the server does not become
        reachable within the configured timeout.
        """
        if await self._is_healthy():
            return False

        self._process = subprocess.Popen(
            [
                "uvicorn",
                self._app_module,
                "--host",
                self._host,
                "--port",
                str(self._port),
            ]
        )

        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            await asyncio.sleep(self._poll_interval)
            if await self._is_healthy():
                return True

        # Timed out — clean up the process we started
        self._process.terminate()
        try:
            self._process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._process.kill()
        self._process = None

        raise RuntimeError(
            f"API server did not become reachable within {self._timeout}s "
            f"(health URL: {self.health_url})"
        )

    def stop(self) -> None:
        """Terminate the uvicorn subprocess if this launcher started it.

        Does nothing if the server was already running before start_if_needed()
        was called (requirement 1.5).
        """
        if self._process is None:
            return
        self._process.terminate()
        try:
            self._process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._process.kill()
        self._process = None

    async def _is_healthy(self) -> bool:
        """Return True if GET /health responds with HTTP 200."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.health_url, timeout=2.0)
                return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException, OSError):
            return False
