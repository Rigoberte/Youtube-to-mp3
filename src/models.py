"""Modelos de dominio para la aplicacion."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class DownloadResult:
    """Representa el resultado de una descarga exitosa."""

    source_url: str
    title: str
    artist: str
    file_path: Path
