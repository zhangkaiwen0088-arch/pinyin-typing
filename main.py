"""Entry point for the pinyin typing trainer."""

from __future__ import annotations

import sys
import traceback


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
    _enable_dpi_awareness()

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

    try:
        from app import run
    except Exception:
        _show_error("启动失败", traceback.format_exc())
        return 1

    try:
        run()
    except Exception:
        _show_error("运行出错", traceback.format_exc())
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
