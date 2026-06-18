"""Interfaz grafica de la aplicacion."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    from .downloader_service import DownloadService, DownloadServiceError
except ImportError:  # pragma: no cover - fallback for direct script execution
    from downloader_service import DownloadService, DownloadServiceError


class DownloadApp:
    """Aplicacion Tkinter para descargar y etiquetar MP3."""

    BG = "#f1f5f9"
    CARD = "#ffffff"
    INK = "#0f172a"
    MUTED = "#64748b"
    ACCENT = "#2563eb"
    ACCENT_DARK = "#1d4ed8"
    SUCCESS = "#16a34a"
    ERROR = "#dc2626"

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("YouTube to MP3 Studio")
        self.root.geometry("1040x760")
        self.root.minsize(920, 680)
        self.root.configure(bg=self.BG)

        self.message_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.output_dir_var = tk.StringVar(value=str(Path.home() / "Downloads" / "YoutubeMP3"))
        self.status_var = tk.StringVar(value="Listo para descargar")
        self.progress_mode = tk.StringVar(value="idle")
        self.item_count_var = tk.StringVar(value="0 enlaces")

        self._configure_style()
        self._build_ui()
        self.root.after(120, self._process_queue)

    def run(self) -> None:
        self.root.mainloop()

    def _configure_style(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("App.TFrame", background=self.BG)
        style.configure("Card.TFrame", background=self.CARD)
        style.configure("Hero.TFrame", background=self.INK)
        style.configure("HeroTitle.TLabel", background=self.INK, foreground="white", font=("Segoe UI", 24, "bold"))
        style.configure("HeroSubtitle.TLabel", background=self.INK, foreground="#cbd5e1", font=("Segoe UI", 10))
        style.configure("Section.TLabel", background=self.CARD, foreground=self.INK, font=("Segoe UI", 12, "bold"))
        style.configure("Body.TLabel", background=self.CARD, foreground=self.MUTED, font=("Segoe UI", 10))
        style.configure("Value.TLabel", background=self.CARD, foreground=self.INK, font=("Segoe UI", 10, "bold"))
        style.configure("Accent.TButton", background=self.ACCENT, foreground="white", padding=(18, 10), font=("Segoe UI", 10, "bold"))
        style.map(
            "Accent.TButton",
            background=[("active", self.ACCENT_DARK), ("pressed", self.ACCENT_DARK)],
            foreground=[("disabled", "#e2e8f0")],
        )
        style.configure("Soft.TButton", background="#e2e8f0", foreground=self.INK, padding=(14, 9), font=("Segoe UI", 10))
        style.map("Soft.TButton", background=[("active", "#cbd5e1")])
        style.configure("TEntry", padding=8)
        style.configure("Horizontal.TProgressbar", troughcolor="#dbeafe", background=self.ACCENT, bordercolor="#dbeafe", lightcolor=self.ACCENT, darkcolor=self.ACCENT)

    def _build_ui(self) -> None:
        self.root.configure(padx=24, pady=24)

        container = ttk.Frame(self.root, style="App.TFrame")
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(2, weight=1)

        hero = tk.Frame(container, bg=self.INK, bd=0, highlightthickness=0)
        hero.grid(row=0, column=0, sticky="ew")
        hero.columnconfigure(0, weight=1)

        hero_inner = ttk.Frame(hero, style="Hero.TFrame")
        hero_inner.pack(fill="both", expand=True, padx=24, pady=22)
        hero_inner.columnconfigure(0, weight=1)

        title = ttk.Label(hero_inner, text="YouTube to MP3 Studio", style="HeroTitle.TLabel")
        title.grid(row=0, column=0, sticky="w")

        subtitle = ttk.Label(
            hero_inner,
            text="Convierte enlaces de YouTube y YouTube Music a MP3 con metadatos limpios y una interfaz clara.",
            style="HeroSubtitle.TLabel",
            wraplength=900,
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(8, 0))

        summary_row = ttk.Frame(hero_inner, style="Hero.TFrame")
        summary_row.grid(row=2, column=0, sticky="w", pady=(16, 0))

        self.summary_label = ttk.Label(summary_row, textvariable=self.item_count_var, style="HeroSubtitle.TLabel")
        self.summary_label.grid(row=0, column=0, sticky="w", padx=(0, 16))

        self.runtime_label = ttk.Label(summary_row, textvariable=self.status_var, style="HeroSubtitle.TLabel")
        self.runtime_label.grid(row=0, column=1, sticky="w")

        cards = ttk.Frame(container, style="App.TFrame")
        cards.grid(row=1, column=0, sticky="ew", pady=(20, 20))
        cards.columnconfigure(0, weight=3)
        cards.columnconfigure(1, weight=2)

        inputs_card = tk.Frame(cards, bg=self.CARD, bd=0, highlightthickness=1, highlightbackground="#dbe3f0")
        inputs_card.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        inputs_card.columnconfigure(0, weight=1)

        inputs_inner = ttk.Frame(inputs_card, style="Card.TFrame", padding=20)
        inputs_inner.pack(fill="both", expand=True)
        inputs_inner.columnconfigure(0, weight=1)

        ttk.Label(inputs_inner, text="Enlaces", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(inputs_inner, text="Pega una URL por linea. La app procesara cada enlace de forma secuencial.", style="Body.TLabel", wraplength=620).grid(row=1, column=0, sticky="w", pady=(6, 12))

        self.urls_text = tk.Text(
            inputs_inner,
            height=14,
            wrap="word",
            bd=0,
            bg="#f8fafc",
            fg=self.INK,
            insertbackground=self.INK,
            highlightthickness=1,
            highlightbackground="#cbd5e1",
            relief="flat",
            font=("Segoe UI", 10),
        )
        self.urls_text.grid(row=2, column=0, sticky="nsew")
        inputs_inner.rowconfigure(2, weight=1)

        button_row = ttk.Frame(inputs_inner, style="Card.TFrame")
        button_row.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        button_row.columnconfigure(0, weight=1)

        self.download_button = ttk.Button(button_row, text="Descargar MP3", style="Accent.TButton", command=self._start_download)
        self.download_button.grid(row=0, column=1, sticky="e")

        self.clear_button = ttk.Button(button_row, text="Limpiar", style="Soft.TButton", command=self._clear_inputs)
        self.clear_button.grid(row=0, column=0, sticky="w")

        side_card = tk.Frame(cards, bg=self.CARD, bd=0, highlightthickness=1, highlightbackground="#dbe3f0")
        side_card.grid(row=0, column=1, sticky="nsew")
        side_card.columnconfigure(0, weight=1)

        side_inner = ttk.Frame(side_card, style="Card.TFrame", padding=20)
        side_inner.pack(fill="both", expand=True)
        side_inner.columnconfigure(0, weight=1)

        ttk.Label(side_inner, text="Destino", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(side_inner, text="Selecciona la carpeta donde se guardaran los MP3.", style="Body.TLabel", wraplength=300).grid(row=1, column=0, sticky="w", pady=(6, 12))

        self.output_entry = ttk.Entry(side_inner, textvariable=self.output_dir_var)
        self.output_entry.grid(row=2, column=0, sticky="ew")

        browse_button = ttk.Button(side_inner, text="Buscar carpeta", style="Soft.TButton", command=self._browse_output_dir)
        browse_button.grid(row=3, column=0, sticky="ew", pady=(12, 0))

        ttk.Label(side_inner, text="Progreso", style="Section.TLabel").grid(row=4, column=0, sticky="w", pady=(24, 8))
        self.progress = ttk.Progressbar(side_inner, mode="indeterminate", length=260, style="Horizontal.TProgressbar")
        self.progress.grid(row=5, column=0, sticky="ew")

        ttk.Label(side_inner, text="Consejo", style="Section.TLabel").grid(row=6, column=0, sticky="w", pady=(24, 8))
        ttk.Label(
            side_inner,
            text="Asegurate de tener ffmpeg instalado en el PATH para que la conversion a MP3 funcione correctamente.",
            style="Body.TLabel",
            wraplength=300,
        ).grid(row=7, column=0, sticky="w")

        log_card = tk.Frame(container, bg=self.CARD, bd=0, highlightthickness=1, highlightbackground="#dbe3f0")
        log_card.grid(row=2, column=0, sticky="nsew")
        log_card.columnconfigure(0, weight=1)
        log_card.rowconfigure(1, weight=1)

        log_inner = ttk.Frame(log_card, style="Card.TFrame", padding=20)
        log_inner.pack(fill="both", expand=True)
        log_inner.columnconfigure(0, weight=1)
        log_inner.rowconfigure(1, weight=1)

        ttk.Label(log_inner, text="Registro", style="Section.TLabel").grid(row=0, column=0, sticky="w")

        log_box = ttk.Frame(log_inner, style="Card.TFrame")
        log_box.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        log_box.columnconfigure(0, weight=1)
        log_box.rowconfigure(0, weight=1)

        self.log_text = tk.Text(
            log_box,
            height=10,
            wrap="word",
            state="disabled",
            bd=0,
            bg="#0f172a",
            fg="#e2e8f0",
            insertbackground="#e2e8f0",
            highlightthickness=1,
            highlightbackground="#1e293b",
            relief="flat",
            font=("Consolas", 10),
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")

        log_scroll = ttk.Scrollbar(log_box, orient="vertical", command=self.log_text.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=log_scroll.set)

    def _browse_output_dir(self) -> None:
        selected_folder = filedialog.askdirectory(title="Selecciona una carpeta de salida")
        if selected_folder:
            self.output_dir_var.set(selected_folder)

    def _clear_inputs(self) -> None:
        self.urls_text.delete("1.0", "end")
        self.item_count_var.set("0 enlaces")
        self.status_var.set("Listo para descargar")

    def _set_busy(self, busy: bool) -> None:
        self.download_button.configure(state="disabled" if busy else "normal")
        self.clear_button.configure(state="disabled" if busy else "normal")
        if busy:
            self.progress.start(12)
            self.progress_mode.set("busy")
        else:
            self.progress.stop()
            self.progress_mode.set("idle")

    def _start_download(self) -> None:
        urls = self._parse_urls(self.urls_text.get("1.0", "end"))
        if not urls:
            messagebox.showwarning("Faltan URLs", "Ingresa al menos una URL valida.")
            return

        output_dir = Path(self.output_dir_var.get().strip()).expanduser()
        self.item_count_var.set(f"{len(urls)} enlace(s)")
        self._set_busy(True)
        self.status_var.set("Descarga en curso...")
        self._append_log("Inicio de proceso")
        self._append_log(f"Destino: {output_dir}")

        worker = threading.Thread(target=self._download_worker, args=(urls, output_dir), daemon=True)
        worker.start()

    def _download_worker(self, urls: list[str], output_dir: Path) -> None:
        service = DownloadService(output_dir=output_dir)

        try:
            results = service.download(urls, progress_callback=self._queue_log)
        except DownloadServiceError as exc:
            self.message_queue.put(("error", str(exc)))
        except Exception as exc:  # pragma: no cover - safety net for unexpected failures
            self.message_queue.put(("error", f"Error inesperado: {exc}"))
        else:
            self.message_queue.put(("done", f"Descargas completadas: {len(results)} archivo(s)"))

    def _process_queue(self) -> None:
        try:
            while True:
                kind, message = self.message_queue.get_nowait()
                if kind == "log":
                    self._append_log(message)
                    self.status_var.set(message)
                elif kind == "error":
                    self._append_log(message)
                    self.status_var.set("La descarga fallo")
                    self._set_busy(False)
                    messagebox.showerror("Error", message)
                elif kind == "done":
                    self._append_log(message)
                    self.status_var.set(message)
                    self._set_busy(False)
                    messagebox.showinfo("Completado", message)
        except queue.Empty:
            pass
        finally:
            self.root.after(120, self._process_queue)

    def _queue_log(self, message: str) -> None:
        self.message_queue.put(("log", message))

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _parse_urls(self, raw_text: str) -> list[str]:
        return [line.strip() for line in raw_text.splitlines() if line.strip()]
