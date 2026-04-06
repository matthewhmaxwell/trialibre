"""
System tray application for Trialibre.
Provides a menu-bar icon on macOS / system tray on Linux/Windows
that controls the backend server and opens the UI.
"""

import subprocess
import sys
import signal
import webbrowser
import threading
import os
from pathlib import Path

# Only import if running as tray app
try:
    import rumps  # macOS menu bar (pip install rumps)
    HAS_RUMPS = True
except ImportError:
    HAS_RUMPS = False

try:
    import pystray  # cross-platform tray (pip install pystray pillow)
    from PIL import Image
    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False


class TrialibreServer:
    """Manages the uvicorn subprocess."""

    def __init__(self, port: int = 8000):
        self.port = port
        self.process: subprocess.Popen | None = None

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def start(self) -> None:
        if self.running:
            return
        self.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "ctm.api.app:app",
             "--host", "127.0.0.1", "--port", str(self.port)],
            cwd=str(Path(__file__).resolve().parents[2]),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def stop(self) -> None:
        if self.process and self.running:
            self.process.send_signal(signal.SIGTERM)
            self.process.wait(timeout=5)
            self.process = None

    def open_browser(self) -> None:
        webbrowser.open(f"http://127.0.0.1:{self.port}")


def run_macos_tray() -> None:
    """macOS menu bar app using rumps."""
    server = TrialibreServer()

    class TrialibreApp(rumps.App):
        def __init__(self):
            super().__init__("Trialibre", icon=None, quit_button=None)
            self.menu = [
                rumps.MenuItem("Open Trialibre", callback=self.open_ui),
                None,  # separator
                rumps.MenuItem("Start Server", callback=self.toggle_server),
                rumps.MenuItem("Server Status: Stopped"),
                None,
                rumps.MenuItem("Quit", callback=self.quit_app),
            ]
            # Auto-start server
            server.start()
            self._update_status()

        def open_ui(self, _):
            if not server.running:
                server.start()
                import time; time.sleep(2)
            server.open_browser()

        def toggle_server(self, sender):
            if server.running:
                server.stop()
            else:
                server.start()
            self._update_status()

        def _update_status(self):
            status = self.menu["Server Status: Stopped"] if not server.running else None
            if server.running:
                self.menu["Start Server"].title = "Stop Server"
                self.title = "Trialibre ●"
            else:
                self.menu["Start Server"].title = "Start Server"
                self.title = "Trialibre ○"

        def quit_app(self, _):
            server.stop()
            rumps.quit_application()

    TrialibreApp().run()


def run_cross_platform_tray() -> None:
    """Cross-platform tray using pystray + Pillow."""
    server = TrialibreServer()
    server.start()

    # Create a simple icon (green circle)
    img = Image.new("RGB", (64, 64), "white")
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.ellipse([8, 8, 56, 56], fill="green")

    def on_open(icon, item):
        server.open_browser()

    def on_toggle(icon, item):
        if server.running:
            server.stop()
        else:
            server.start()

    def on_quit(icon, item):
        server.stop()
        icon.stop()

    icon = pystray.Icon(
        "Trialibre",
        img,
        "Trialibre",
        menu=pystray.Menu(
            pystray.MenuItem("Open Trialibre", on_open, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Toggle Server", on_toggle),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", on_quit),
        ),
    )
    icon.run()


def main() -> None:
    """Launch the best available tray implementation."""
    if sys.platform == "darwin" and HAS_RUMPS:
        run_macos_tray()
    elif HAS_PYSTRAY:
        run_cross_platform_tray()
    else:
        print("No system tray library available.")
        print("Install 'rumps' (macOS) or 'pystray pillow' (cross-platform).")
        print("Falling back to CLI server mode...")
        from ctm.cli.main import main as cli_main
        sys.argv = ["trialibre", "serve"]
        cli_main()


if __name__ == "__main__":
    main()
