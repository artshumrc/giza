"""Rich multi-step progress display for the compile pipeline.

The display renders one row per pipeline phase plus dedicated, detailed
progress bars for the two long-running phases (HTML extraction/ingest and
brotli compression). When the output stream is not an interactive terminal
(or ``rich`` is unavailable), the display degrades to a no-op so piped logs
and CI output stay clean; callers fall back to plain-text reporting.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from collections.abc import Callable, Iterator
from typing import TextIO

try:
    from rich.console import Console
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TextColumn,
        TimeElapsedColumn,
    )

    _RICH_AVAILABLE = True
except ImportError:  # pragma: no cover - rich is a declared dependency
    _RICH_AVAILABLE = False


# Ordered pipeline phases shown in the overall step tracker. Each entry is a
# (key, human label) pair; ``set_phase`` is called with the key.
_PHASES: tuple[tuple[str, str], ...] = (
    ("validation", "Validating config"),
    ("discovery", "Discovering pages"),
    ("table_creation", "Creating tables"),
    ("extraction_ingest", "Processing HTML files"),
    ("index_creation", "Building indexes"),
    ("fts_optimize", "Optimizing full-text index"),
    ("vacuum_into", "Compacting database"),
    ("hashing", "Hashing database"),
    ("post_build_checks", "Verifying database"),
    ("compression", "Compressing database"),
    ("manifest_write", "Writing manifest"),
    ("client_write", "Writing client"),
)
_PHASE_INDEX = {key: index for index, (key, _) in enumerate(_PHASES)}


def _format_bytes(num_bytes: float) -> str:
    value = float(num_bytes)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024.0 or unit == "GiB":
            return f"{value:,.1f} {unit}" if unit != "B" else f"{int(value):,} B"
        value /= 1024.0
    return f"{value:,.1f} GiB"


def _format_duration(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "--:--"
    total = int(seconds)
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


class CompileProgress:
    """Live, multi-row progress UI for :func:`dredge.compiler.compile_site`.

    Safe to instantiate unconditionally: when the stream is not a TTY or rich
    is unavailable, :attr:`enabled` is ``False`` and every method is a no-op.
    """

    def __init__(self, stream: TextIO | None) -> None:
        self.enabled = bool(_RICH_AVAILABLE and stream is not None and stream.isatty())
        self._progress: Progress | None = None
        self._overall_task: int | None = None
        self._files_task: int | None = None
        self._compress_task: int | None = None
        if not self.enabled:
            return
        console = Console(file=stream, stderr=True)
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=None),
            TextColumn("{task.fields[detail]}"),
            TimeElapsedColumn(),
            console=console,
            transient=False,
            refresh_per_second=12,
        )

    @contextmanager
    def activate(self) -> Iterator["CompileProgress"]:
        """Start the live display for the duration of the ``with`` block."""
        if not self.enabled or self._progress is None:
            yield self
            return
        with self._progress:
            self._overall_task = self._progress.add_task(
                "[bold]Compiling[/bold]",
                total=len(_PHASES),
                detail="",
            )
            yield self

    def set_phase(self, key: str) -> None:
        """Advance the overall step tracker to the named phase."""
        if self._progress is None or self._overall_task is None:
            return
        index = _PHASE_INDEX.get(key)
        if index is None:
            return
        label = _PHASES[index][1]
        self._progress.update(
            self._overall_task,
            completed=index,
            detail=f"[dim]{label}[/dim]",
        )

    def finish(self) -> None:
        """Mark the overall tracker complete."""
        if self._progress is None or self._overall_task is None:
            return
        self._progress.update(
            self._overall_task,
            completed=len(_PHASES),
            detail="[green]done[/green]",
        )

    def begin_files(self, total: int) -> Callable[[int, int | None], None]:
        """Add the ingest bar and return an ``advance(processed, db_bytes)``.

        ``processed`` is the absolute count of documents handled so far;
        ``db_bytes`` is the current build database size (or ``None``).
        """
        if self._progress is None:
            return lambda processed, db_bytes=None: None
        task = self._progress.add_task(
            "Processing HTML files",
            total=total,
            detail="",
        )
        self._files_task = task
        started = time.perf_counter()

        def advance(processed: int, db_bytes: int | None = None) -> None:
            elapsed = max(time.perf_counter() - started, 1e-6)
            rate = processed / elapsed
            remaining = max(total - processed, 0)
            eta = remaining / rate if rate > 0 else None
            size = f" · {_format_bytes(db_bytes)}" if db_bytes is not None else ""
            detail = (
                f"{processed:,}/{total:,} · {rate:,.0f}/s · "
                f"ETA {_format_duration(eta)}{size}"
            )
            self._progress.update(task, completed=processed, detail=detail)

        return advance

    def begin_compression(self, total_bytes: int) -> Callable[[int], None]:
        """Add the compression bar and return an ``advance(n_bytes)``."""
        if self._progress is None:
            return lambda n_bytes: None
        task = self._progress.add_task(
            "Compressing database",
            total=total_bytes,
            detail="",
        )
        self._compress_task = task
        started = time.perf_counter()
        processed = 0

        def advance(n_bytes: int) -> None:
            nonlocal processed
            processed += n_bytes
            elapsed = max(time.perf_counter() - started, 1e-6)
            speed = processed / elapsed
            detail = (
                f"{_format_bytes(processed)}/{_format_bytes(total_bytes)} · "
                f"{_format_bytes(speed)}/s"
            )
            self._progress.update(task, completed=processed, detail=detail)

        return advance
