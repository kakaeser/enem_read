"""MobileServerLauncher: serves the mobile upload page over LAN via a daemon HTTP thread."""

import errno
import http.server
import logging
import os
import socket
import socketserver
import threading

logger = logging.getLogger(__name__)


class _DirectoryHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler that serves files from a fixed directory."""

    # Set per-instance via a class-level attribute injected before construction
    _serve_dir: str = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=self.__class__._serve_dir, **kwargs)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        """Suppress default stderr logging; route through Python logging instead."""
        logger.debug("MobileServer: " + format, *args)


class MobileServerLauncher:
    """Starts a lightweight static HTTP server in a daemon thread.

    Serves *mobile_dir* over the local network so mobile participants can
    access the upload page via a URL of the form
    ``http://{lan_ip}:{port}/index.html``.

    Requirements: 2.1, 2.2, 2.3, 2.4
    """

    def __init__(self, mobile_dir: str, port: int = 8080) -> None:
        self._mobile_dir = os.path.abspath(mobile_dir)
        self._port = port
        self._actual_port: int | None = None
        self._lan_ip: str | None = None
        self._server: socketserver.TCPServer | None = None
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> str:
        """Start the static file server.

        Returns the full URL ``http://{lan_ip}:{port}/index.html``.

        Raises
        ------
        OSError
            If all three port candidates (port, port+1, port+2) are in use.
        """
        self._lan_ip = self._detect_lan_ip()
        self._server = self._bind_server()
        self._actual_port = self._server.server_address[1]

        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
            name="MobileServerThread",
        )
        self._thread.start()
        logger.info("MobileServer started at %s", self.url)
        return self.url

    def stop(self) -> None:
        """Shut down the background HTTP server thread (Requirement 2.4)."""
        if self._server is not None:
            self._server.shutdown()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("MobileServer stopped.")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def url(self) -> str:
        """Return ``http://{lan_ip}:{actual_port}/index.html``."""
        if self._lan_ip is None or self._actual_port is None:
            raise RuntimeError("MobileServerLauncher has not been started yet.")
        return f"http://{self._lan_ip}:{self._actual_port}/index.html"

    @property
    def lan_ip(self) -> str:
        """Return the detected (or fallback) LAN IP address."""
        if self._lan_ip is None:
            raise RuntimeError("MobileServerLauncher has not been started yet.")
        return self._lan_ip

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _detect_lan_ip(self) -> str:
        """Detect the machine's LAN IP address.

        Iterates ``socket.getaddrinfo(socket.gethostname(), None)`` and
        returns the first non-loopback IPv4 address found.  Falls back to
        ``127.0.0.1`` with a logged warning if detection fails
        (Requirement 2.2).
        """
        try:
            hostname = socket.gethostname()
            results = socket.getaddrinfo(hostname, None)
            for result in results:
                family, _, _, _, sockaddr = result
                if family == socket.AF_INET:
                    ip = sockaddr[0]
                    if not ip.startswith("127."):
                        return ip
        except OSError as exc:
            logger.warning(
                "LAN IP detection failed (%s); falling back to 127.0.0.1", exc
            )
            return "127.0.0.1"

        # No non-loopback IPv4 found
        logger.warning(
            "No non-loopback IPv4 address found; falling back to 127.0.0.1. "
            "Mobile sharing over LAN will be unavailable."
        )
        return "127.0.0.1"

    def _bind_server(self) -> socketserver.TCPServer:
        """Try to bind an HTTPServer on port, port+1, port+2.

        Raises ``OSError`` if all three candidates are in use
        (Requirement 2.3).
        """
        # Build a handler class that is bound to the correct directory.
        # We create a fresh subclass so that concurrent instances don't
        # interfere with each other's _serve_dir class attribute.
        serve_dir = self._mobile_dir

        class BoundHandler(_DirectoryHandler):
            _serve_dir = serve_dir

        for attempt in range(3):
            candidate_port = self._port + attempt
            try:
                server = http.server.HTTPServer(
                    ("", candidate_port), BoundHandler
                )
                server.allow_reuse_address = True
                return server
            except OSError as exc:
                if exc.errno in (errno.EADDRINUSE, errno.EACCES):
                    logger.warning(
                        "Port %d in use, trying %d",
                        candidate_port,
                        candidate_port + 1,
                    )
                    continue
                raise  # Unexpected OS error — propagate immediately

        raise OSError(
            f"All port candidates ({self._port}, {self._port + 1}, "
            f"{self._port + 2}) are already in use."
        )
