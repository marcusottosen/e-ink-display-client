"""Fixed E673 hardware adapter and a lock-protected refresh worker."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Protocol

from PIL import Image

EXPECTED_RESOLUTION = (800, 480)


class DisplayDriver(Protocol):
    def show(self, image_path: Path) -> None: ...


class FixedE673Driver:
    """Use the known E673 driver directly; the Pi never resizes artifacts."""

    def __init__(self) -> None:
        try:
            from inky.inky_e673 import Inky  # type: ignore[import-not-found]
        except ImportError as error:
            raise RuntimeError("Install the Inky library before enabling E673 hardware") from error
        self._display = Inky(resolution=EXPECTED_RESOLUTION)
        if self._display.resolution != EXPECTED_RESOLUTION:
            raise RuntimeError("configured E673 driver did not expose the expected 800x480 panel")

    def show(self, image_path: Path) -> None:
        with Image.open(image_path) as image:
            if image.size != EXPECTED_RESOLUTION or image.mode != "RGB":
                raise ValueError("Pi refuses non-RGB or non-800x480 artifacts")
            self._display.set_image(image)
        # E673.show() blocks until the physical refresh sequence completes.
        self._display.show()

class NoopDisplayDriver:
    """Development-only driver for network and spool verification."""

    def show(self, image_path: Path) -> None:
        if not image_path.is_file():
            raise FileNotFoundError(image_path)


class SerializedDisplayWorker:
    """Guarantee that at most one physical e-ink update runs at a time."""

    def __init__(self, driver: DisplayDriver) -> None:
        self._driver = driver
        self._lock = threading.Lock()

    def refresh(self, image_path: Path) -> None:
        with self._lock:
            self._driver.show(image_path)
