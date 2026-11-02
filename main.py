"""Entry point for the pinyin typing trainer."""

from __future__ import annotations

import os
import sys
import traceback


def _debug(message: str) -> None:
    if os.environ.get("PINYIN_DEBUG") == "1":
        print(f"[pinyin-debug] {message}", file=sys.stderr, flush=True)


def _enable_dpi_awareness() -> None:
    """Make Tk use crisp physical pixels on high-DPI Windows displays."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            import ctypes

            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _show_error(title: str, message: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message, parent=root)
        root.destroy()
    except Exception:
        print(f"{title}\n{message}", file=sys.stderr)


def main() -> int:
    if os.environ.get("PINYIN_DEBUG") == "1":
        import faulthandler

        faulthandler.dump_traceback_later(10, repeat=True)
        _debug("main start")
    _enable_dpi_awareness()
    _debug("dpi enabled")

    try:
        import pypinyin  # noqa: F401
    except ImportError:
        _show_error(
            "缺少拼音库",
            "当前 Python 环境没有安装 pypinyin。\n\n"
            "请在 C:\\py 下执行：\n"
            "    pixi add pypinyin\n\n"
            "然后重新启动本程序。",
        )
        return 1
    _debug("pypinyin imported")

    try:
        from app import run
    except Exception:
        _show_error("启动失败", traceback.format_exc())
        return 1
    _debug("app imported")

    try:
        _debug("calling run")
        run()
    except Exception:
        _show_error("运行出错", traceback.format_exc())
        return 1
    _debug("run returned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
