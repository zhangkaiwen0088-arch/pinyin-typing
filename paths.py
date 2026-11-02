"""Runtime paths that work both from source and from a PyInstaller EXE."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))

if FROZEN:
    DATA_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", DATA_DIR))
else:
    DATA_DIR = Path(__file__).resolve().parent
    RESOURCE_DIR = DATA_DIR


def _ensure_sentences() -> Path:
    """Keep the sentence bank editable next to the EXE.

    The bundled copy is used on first launch, then persisted beside the
    executable.  If that folder is read-only, fall back to the bundled file
    so the app can still run.
    """
    target = DATA_DIR / "sentences.txt"
    source = RESOURCE_DIR / "sentences.txt"
    if target.exists():
        return target
    if source.exists() and source != target:
        try:
            shutil.copyfile(source, target)
        except OSError:
            return source
    return target if target.exists() else source


SENTENCES_FILE = _ensure_sentences()
SETTINGS_FILE = DATA_DIR / ".settings.json"
STATS_FILE = DATA_DIR / ".stats.json"
DAILY_FILE = DATA_DIR / ".daily.json"
