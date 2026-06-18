"""Punto de entrada de la aplicacion."""

try:
	from .ui import DownloadApp
except ImportError:  # pragma: no cover - fallback for direct script execution
	from ui import DownloadApp


def main() -> None:
	app = DownloadApp()
	app.run()


if __name__ == "__main__":
	main()
