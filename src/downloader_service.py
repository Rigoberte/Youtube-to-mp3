"""Servicio de descarga y etiquetado de audio."""

from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path
from typing import Callable, Iterable

import imageio_ffmpeg
from mutagen.id3 import ID3, ID3NoHeaderError, TIT2, TPE1, TPE2
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError as YtDlpDownloadError

try:
    from .models import DownloadResult
except ImportError:  # pragma: no cover - fallback for direct script execution
    from models import DownloadResult

ProgressCallback = Callable[[str], None]


class DownloadServiceError(RuntimeError):
    """Error de alto nivel para la capa de descarga."""


class DownloadService:
    """Descarga audios de YouTube o YouTube Music y los normaliza a MP3."""

    def __init__(self, output_dir: Path, quality: str = "192") -> None:
        self.output_dir = output_dir
        self.quality = quality

    def download(self, urls: Iterable[str], progress_callback: ProgressCallback | None = None) -> list[DownloadResult]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        ffmpeg_executable = self._resolve_ffmpeg_executable()
        results: list[DownloadResult] = []

        for url in urls:
            clean_url = url.strip()
            if not clean_url:
                continue

            self._emit(progress_callback, f"Iniciando descarga: {clean_url}")
            result = self._download_single(clean_url, progress_callback, ffmpeg_executable)
            results.append(result)

        return results

    def _download_single(self, url: str, progress_callback: ProgressCallback | None, ffmpeg_executable: str) -> DownloadResult:
        with tempfile.TemporaryDirectory(prefix="youtube-mp3-") as staging_dir_name:
            staging_dir = Path(staging_dir_name)
            options = {
                "format": "bestaudio/best",
                "noplaylist": True,
                "outtmpl": str(staging_dir / "%(id)s.%(ext)s"),
                "ffmpeg_location": ffmpeg_executable,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": self.quality,
                    }
                ],
                "quiet": True,
                "no_warnings": True,
                "windowsfilenames": True,
            }

            try:
                with YoutubeDL(options) as ydl:
                    info = ydl.extract_info(url, download=True)
                    if not info:
                        raise DownloadServiceError("No se pudo obtener informacion del video.")
                    source_path = Path(ydl.prepare_filename(info))
            except YtDlpDownloadError as exc:
                raise DownloadServiceError(f"No se pudo descargar el contenido: {url}") from exc

            mp3_path = source_path.with_suffix(".mp3")
            if not mp3_path.exists():
                raise DownloadServiceError(f"No se encontro el archivo MP3 generado para: {url}")

            artist = self._resolve_artist(info)
            title = self._resolve_title(info, artist)
            final_path = self._build_final_path(artist, title)

            self._write_id3_tags(mp3_path, title, artist)
            final_path.parent.mkdir(parents=True, exist_ok=True)
            if final_path.exists():
                final_path.unlink()
            mp3_path.replace(final_path)

            result = DownloadResult(
                source_url=url,
                title=title,
                artist=artist,
                file_path=final_path,
            )
            return result

    def _resolve_title(self, info: dict[str, object], artist: str) -> str:
        raw_title = self._first_text_value(info, ("track", "title"))
        if not raw_title:
            return "Sin titulo"

        title = raw_title.strip()
        stripped_artist = self._strip_artist_prefix(title, artist)
        cleaned_title = self._strip_common_title_suffixes(stripped_artist)
        return self._clean_text(cleaned_title)

    def _resolve_artist(self, info: dict[str, object]) -> str:
        artist = self._first_text_value(info, ("artist", "contributor", "creator", "channel", "uploader"))
        return self._normalize_artist_name(artist) if artist else "Artista desconocido"

    def _write_id3_tags(self, file_path: Path, title: str, artist: str) -> None:
        try:
            tags = ID3(file_path)
        except ID3NoHeaderError:
            tags = ID3()

        tags.delall("TIT2")
        tags.delall("TPE1")
        tags.add(TIT2(encoding=3, text=title))
        tags.add(TPE1(encoding=3, text=artist))
        tags.save(file_path)

    def _resolve_ffmpeg_executable(self) -> str:
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            return system_ffmpeg

        bundled_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        if bundled_ffmpeg:
            return bundled_ffmpeg

        raise DownloadServiceError(
            "No se pudo encontrar ffmpeg en el sistema ni descargar un binario compatible."
        )

    def _build_final_path(self, artist: str, title: str) -> Path:
        safe_artist = self._sanitize_filename_component(artist)
        safe_title = self._sanitize_filename_component(title)
        return self.output_dir / f"{safe_artist} - {safe_title}.mp3"

    def _first_text_value(self, info: dict[str, object], keys: tuple[str, ...]) -> str:
        for key in keys:
            value = info.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def _strip_artist_prefix(self, title: str, artist: str) -> str:
        if not artist:
            return title

        title_lower = title.lower()
        artist_lower = artist.lower()
        for separator in (" - ", " – ", " — ", ": "):
            prefix = f"{artist_lower}{separator}"
            if title_lower.startswith(prefix):
                return title[len(prefix):].strip()
        return title

    def _clean_text(self, value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value).strip()
        cleaned = cleaned.strip(" ._-\t")
        return cleaned or "Sin titulo"

    def _normalize_artist_name(self, value: str) -> str:
        cleaned = self._clean_text(value)
        cleaned = re.sub(r"\s*[-–—]\s*Topic$", "", cleaned, flags=re.IGNORECASE).strip()
        return cleaned or "Artista desconocido"

    def _strip_common_title_suffixes(self, value: str) -> str:
        cleaned = value.strip()
        suffix_pattern = re.compile(
            r"\s*[\[(](?:official(?:\s+music)?\s+video|official|audio|lyrics?|lyric video|video|visualizer|live|performance|remaster(?:ed)?|version|topic|hq|hd|4k|8k|\d{3,4}p|clean|explicit|edit|shorts?)(?:[^\])\)]*)?[\])]\s*$",
            re.IGNORECASE,
        )
        while True:
            updated = suffix_pattern.sub("", cleaned).strip()
            if updated == cleaned:
                break
            cleaned = updated
        cleaned = re.sub(r"\s*[-–—]\s*Topic$", "", cleaned, flags=re.IGNORECASE).strip()
        return cleaned

    def _sanitize_filename_component(self, value: str) -> str:
        cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", value)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ._-\t")
        return cleaned or "Sin nombre"

    def _emit(self, progress_callback: ProgressCallback | None, message: str) -> None:
        if progress_callback is not None:
            progress_callback(message)
