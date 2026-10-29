"""Tkinter interface for the pinyin typing trainer."""

from __future__ import annotations

import json
import os
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import font as tkfont
from tkinter import messagebox

from trainer import (
    Analysis,
    Sentence,
    SentenceBag,
    SentenceLibrary,
    analyse,
    format_duration,
    load_sentences,
    speed_cpm,
)

APP_DIR = Path(__file__).resolve().parent
SENTENCES_FILE = APP_DIR / "sentences.txt"
SETTINGS_FILE = APP_DIR / ".settings.json"

MIN_FONT_SIZE = 32
MAX_FONT_SIZE = 96
DEFAULT_FONT_SIZE = 56
FONT_STEP = 4


@dataclass(frozen=True, slots=True)
class Theme:
    key: str
    label: str
    bg: str
    surface: str
    surface_alt: str
    border: str
    text: str
    muted: str
    faint: str
    accent: str
    accent_hover: str
    accent_fg: str
    accent_soft: str
    button_bg: str
    button_hover: str
    current_bg: str
    current_fg: str
    current_ring: str
    done: str
    done_soft: str
    error: str
    error_soft: str
    selection: str


THEMES: dict[str, Theme] = {
    "light": Theme(
        key="light",
        label="亮色",
        bg="#F2EEE5",
        surface="#FFFCF6",
        surface_alt="#F6F1E7",
        border="#E2D8C8",
        text="#2B2720",
        muted="#7D7365",
        faint="#B8AD9D",
        accent="#B45309",
        accent_hover="#92400E",
        accent_fg="#FFFFFF",
        accent_soft="#FCE7C4",
        button_bg="#EAE2D3",
        button_hover="#DED2BE",
        current_bg="#FFD166",
        current_fg="#20190B",
        current_ring="#D97706",
        done="#147A5B",
        done_soft="#DCF2E9",
        error="#B42318",
        error_soft="#FDE8E6",
        selection="#F5D9A8",
    ),
    "dark": Theme(
        key="dark",
        label="暗色",
        bg="#0D1117",
        surface="#151B24",
        surface_alt="#1C2430",
        border="#2A3442",
        text="#EEF2F7",
        muted="#99A5B6",
        faint="#5C697B",
        accent="#F4B94A",
        accent_hover="#FFD166",
        accent_fg="#191204",
        accent_soft="#3A2E12",
        button_bg="#222B37",
        button_hover="#2C3745",
        current_bg="#FFD166",
        current_fg="#191204",
        current_ring="#FFE08A",
        done="#5FE3B8",
        done_soft="#11382E",
        error="#FF8C82",
        error_soft="#421F1D",
        selection="#554019",
    ),
}


class ThemedButton(tk.Button):
    """A flat button that can repaint itself when the theme changes."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        text: str,
        command,
        kind: str = "soft",
        font=None,
        padx: int = 12,
        pady: int = 7,
        **kwargs,
    ) -> None:
        self.kind = kind
        self._theme: Theme | None = None
        self._hovering = False
        self._selected = False
        self._normal_bg = "#dddddd"
        self._hover_bg = "#cccccc"
        super().__init__(
            master,
            text=text,
            command=command,
            font=font,
            padx=padx,
            pady=pady,
            relief="flat",
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            takefocus=0,
            **kwargs,
        )
        self.bind("<Enter>", self._on_enter, add="+")
        self.bind("<Leave>", self._on_leave, add="+")

    def set_theme(self, theme: Theme, selected: bool = False) -> None:
        self._theme = theme
        self._selected = selected

        if self.kind == "primary":
            bg = theme.accent
            hover = theme.accent_hover
            fg = theme.accent_fg
        elif self.kind == "segment" and selected:
            bg = theme.accent
            hover = theme.accent_hover
            fg = theme.accent_fg
        elif self.kind == "segment":
            bg = theme.button_bg
            hover = theme.button_hover
            fg = theme.text
        elif self.kind == "ghost":
            bg = theme.surface
            hover = theme.button_bg
            fg = theme.muted
        else:
            bg = theme.button_bg
            hover = theme.button_hover
            fg = theme.text

        self._normal_bg = bg
        self._hover_bg = hover
        active_bg = hover if self._hovering else bg
        self.configure(
            bg=active_bg,
            fg=fg,
            activebackground=hover,
            activeforeground=fg,
            disabledforeground=theme.faint,
            highlightbackground=bg,
            highlightcolor=bg,
        )

    def _on_enter(self, _event=None) -> None:
        self._hovering = True
        if self._theme is not None:
            self.configure(bg=self._hover_bg)

    def _on_leave(self, _event=None) -> None:
        self._hovering = False
        if self._theme is not None:
            self.configure(bg=self._normal_bg)


class ThemeToggle(tk.Frame):
    """Small segmented control for the light/dark theme."""

    def __init__(self, master: tk.Misc, *, font, on_change) -> None:
        super().__init__(master, bd=0, highlightthickness=0)
        self._on_change = on_change
        self.buttons: dict[str, ThemedButton] = {}
        for key in ("light", "dark"):
            button = ThemedButton(
                self,
                text=THEMES[key].label,
                command=lambda value=key: self._on_change(value),
                kind="segment",
                font=font,
                padx=11,
                pady=5,
            )
            button.pack(side="left", padx=2, pady=2)
            self.buttons[key] = button

    def apply_theme(self, theme: Theme, active_key: str) -> None:
        self.configure(bg=theme.surface_alt)
        for key, button in self.buttons.items():
            button.set_theme(theme, selected=(key == active_key))


class PinyinTrainerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("拼音打字练习")
        self.root.minsize(1040, 740)
        self.root.geometry(self._centred_geometry(1240, 880))
        self.root.configure(bg=THEMES["light"].bg)

        self.settings = self._load_settings()
        theme_key = self.settings.get("theme", "light")
        self.theme_key = (
            theme_key
            if isinstance(theme_key, str) and theme_key in THEMES
            else "light"
        )
        self.theme = THEMES[self.theme_key]

        try:
            loaded_font_size = int(
                self.settings.get("font_size", DEFAULT_FONT_SIZE)
            )
        except (TypeError, ValueError):
            loaded_font_size = DEFAULT_FONT_SIZE
        self.font_px = self._clamp_font(loaded_font_size)
        self._pick_fonts()

        self.library: SentenceLibrary | None = None
        self.bag: SentenceBag | None = None
        self.sentence: Sentence | None = None
        self.analysis: Analysis | None = None

        self.started_at: float | None = None
        self.finished_at: float | None = None
        self._tick_job: str | None = None
        self._layout_job: str | None = None
        self._last_card_width = 0

        self._status_text = "输入第一个字母后开始计时。"
        self._status_kind = "muted"

        self.timer_var = tk.StringVar(value="00:00.0")
        self.progress_var = tk.StringVar(value="0 / 0 字")
        self.speed_var = tk.StringVar(value="— 字/分")
        self.font_size_var = tk.StringVar(value=str(self.font_px))

        self.char_labels: list[tk.Label] = []

        self._build_ui()
        self._apply_theme()
        self._load_library(initial=True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Return>", self._on_return)
        self.root.bind("<KP_Enter>", self._on_return)
        self.root.bind("<Control-r>", self._on_restart)
        self.root.bind("<Control-R>", self._on_restart)
        self.root.bind("<Control-plus>", self._on_font_increase)
        self.root.bind("<Control-equal>", self._on_font_increase)
        self.root.bind("<Control-minus>", self._on_font_decrease)
        self.root.bind("<Control-MouseWheel>", self._on_mousewheel_font)
        self.root.bind("<F5>", self._on_reload_shortcut)
        self.root.after(60, self._schedule_layout)

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------
    def _centred_geometry(self, width: int, height: int) -> str:
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        return f"{width}x{height}+{x}+{y}"

    def _load_settings(self) -> dict:
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, ValueError, TypeError):
            pass
        return {}

    def _save_settings(self) -> None:
        payload = {"theme": self.theme_key, "font_size": self.font_px}
        try:
            SETTINGS_FILE.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass

    def _pick_fonts(self) -> None:
        families = set(tkfont.families(self.root))
        cjk_candidates = (
            "Microsoft YaHei UI",
            "Microsoft YaHei",
            "Noto Sans SC",
            "SimHei",
            "Segoe UI",
        )
        mono_candidates = (
            "Cascadia Mono",
            "Consolas",
            "Courier New",
            "Segoe UI",
        )
        self.cjk_family = next(
            (name for name in cjk_candidates if name in families), "TkDefaultFont"
        )
        self.mono_family = next(
            (name for name in mono_candidates if name in families), "TkFixedFont"
        )

        self.title_font = tkfont.Font(
            self.root, family=self.cjk_family, size=-28, weight="bold"
        )
        self.subtitle_font = tkfont.Font(
            self.root, family=self.cjk_family, size=-13
        )
        self.ui_font = tkfont.Font(self.root, family=self.cjk_family, size=-14)
        self.small_font = tkfont.Font(self.root, family=self.cjk_family, size=-12)
        self.caption_font = tkfont.Font(
            self.root, family=self.cjk_family, size=-11, weight="bold"
        )
        self.button_font = tkfont.Font(
            self.root, family=self.cjk_family, size=-13
        )
        self.size_font = tkfont.Font(
            self.root, family=self.mono_family, size=-14, weight="bold"
        )
        self.stat_value_font = tkfont.Font(
            self.root, family=self.mono_family, size=-25, weight="bold"
        )
        self.cjk_font = tkfont.Font(
            self.root, family=self.cjk_family, size=-self.font_px
        )
        self.pinyin_font = tkfont.Font(
            self.root, family=self.mono_family, size=-self._pinyin_size
        )

    @property
    def _pinyin_size(self) -> int:
        return max(20, min(56, round(self.font_px * 0.60)))

    @staticmethod
    def _clamp_font(value: int) -> int:
        if value < MIN_FONT_SIZE:
            return MIN_FONT_SIZE
        if value > MAX_FONT_SIZE:
            return MAX_FONT_SIZE
        # Keep it on a predictable step.
        return MIN_FONT_SIZE + ((value - MIN_FONT_SIZE) // FONT_STEP) * FONT_STEP

    # ------------------------------------------------------------------
    # Widget construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.container = tk.Frame(self.root)
        self.container.pack(fill="both", expand=True, padx=28, pady=20)

        self._build_header()
        self._build_stats()
        self._build_sentence_card()
        self._build_input_card()
        self._build_footer()

    def _build_header(self) -> None:
        self.header = tk.Frame(self.container)
        self.header.pack(fill="x")

        left = tk.Frame(self.header)
        left.pack(side="left")
        self.title_label = tk.Label(left, text="拼音打字练习", font=self.title_font)
        self.title_label.pack(anchor="w")
        self.subtitle_label = tk.Label(
            left,
            text="题库加载中…",
            font=self.subtitle_font,
        )
        self.subtitle_label.pack(anchor="w", pady=(3, 0))

        right = tk.Frame(self.header)
        right.pack(side="right")

        self.next_button = ThemedButton(
            right,
            text="换一句",
            command=self._next_sentence,
            kind="primary",
            font=self.button_font,
            padx=18,
            pady=8,
        )
        self.next_button.pack(side="right")

        self.font_group = tk.Frame(right)
        font_group = self.font_group
        font_group.pack(side="right", padx=(0, 16))
        self.font_caption = tk.Label(
            font_group, text="字号", font=self.small_font
        )
        self.font_caption.pack(side="left", padx=(0, 6))

        self.font_minus = ThemedButton(
            font_group,
            text="A−",
            command=lambda: self._change_font(-FONT_STEP),
            font=self.button_font,
            padx=8,
            pady=5,
        )
        self.font_minus.pack(side="left")
        self.font_value = tk.Label(
            font_group,
            textvariable=self.font_size_var,
            font=self.size_font,
            width=3,
        )
        self.font_value.pack(side="left", padx=4)
        self.font_plus = ThemedButton(
            font_group,
            text="A+",
            command=lambda: self._change_font(FONT_STEP),
            font=self.button_font,
            padx=8,
            pady=5,
        )
        self.font_plus.pack(side="left")

        self.theme_toggle = ThemeToggle(
            right, font=self.button_font, on_change=self._set_theme
        )
        self.theme_toggle.pack(side="right", padx=(0, 16))

    def _build_stats(self) -> None:
        self.stats_frame = tk.Frame(self.container)
        self.stats_frame.pack(fill="x", pady=(18, 0))

        self.stat_cards: list[tk.Frame] = []
        self.stat_captions: list[tk.Label] = []
        self.stat_values: list[tk.Label] = []

        specs = (
            ("计时", self.timer_var),
            ("本句进度", self.progress_var),
            ("速度", self.speed_var),
        )
        for column, (caption, variable) in enumerate(specs):
            card = tk.Frame(self.stats_frame, highlightthickness=1)
            card.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(0, 12) if column < len(specs) - 1 else 0,
            )
            self.stats_frame.columnconfigure(column, weight=1)
            caption_label = tk.Label(card, text=caption, font=self.caption_font)
            caption_label.pack(anchor="w", padx=16, pady=(10, 0))
            value_label = tk.Label(
                card,
                textvariable=variable,
                font=self.stat_value_font,
                anchor="w",
            )
            value_label.pack(fill="x", padx=16, pady=(1, 10))
            self.stat_cards.append(card)
            self.stat_captions.append(caption_label)
            self.stat_values.append(value_label)

    def _build_sentence_card(self) -> None:
        self.sentence_card = tk.Frame(self.container, highlightthickness=1)
        self.sentence_card.pack(fill="both", expand=True, pady=(16, 0))
        self.sentence_card.bind("<Configure>", self._on_sentence_configure)

        self.sentence_content = tk.Frame(self.sentence_card)
        self.sentence_content.pack(expand=True, padx=32, pady=20)

    def _build_input_card(self) -> None:
        self.input_card = tk.Frame(self.container, highlightthickness=1)
        self.input_card.pack(fill="x", pady=(14, 0))

        inner = tk.Frame(self.input_card)
        inner.pack(fill="x", padx=18, pady=(12, 10))

        self.input_top = tk.Frame(inner)
        top = self.input_top
        top.pack(fill="x")
        self.input_title = tk.Label(
            top, text="输入拼音", font=self.ui_font
        )
        self.input_title.pack(side="left")
        self.input_hint = tk.Label(
            top,
            text="无需声调 · 空格自动忽略",
            font=self.small_font,
        )
        self.input_hint.pack(side="right")

        self.input_text = tk.Text(
            inner,
            height=2,
            wrap="char",
            font=self.pinyin_font,
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=14,
            pady=10,
            spacing1=2,
            spacing2=2,
            spacing3=2,
            insertwidth=2,
            undo=False,
        )
        self.input_text.pack(fill="x", pady=(8, 0))
        self.input_text.bind("<KeyRelease>", self._on_key_release)
        self.input_text.bind("<<Paste>>", self._on_paste)
        self.input_text.bind("<<Cut>>", self._on_paste)
        self.input_text.bind("<Return>", self._on_return)
        self.input_text.bind("<KP_Enter>", self._on_return)
        self.input_text.bind("<Shift-Return>", self._on_return)

        self.status_label = tk.Label(
            inner,
            text=self._status_text,
            font=self.small_font,
            anchor="w",
        )
        self.status_label.pack(fill="x", pady=(7, 0))

    def _build_footer(self) -> None:
        self.footer = tk.Frame(self.container)
        self.footer.pack(fill="x", pady=(12, 0))

        self.footer_hint = tk.Label(
            self.footer,
            text="Backspace 删除   ·   Enter 下一句   ·   Ctrl+R 重开   ·   Ctrl+滚轮 调字号",
            font=self.small_font,
            anchor="w",
        )
        self.footer_hint.pack(side="left")

        self.open_button = ThemedButton(
            self.footer,
            text="打开题库",
            command=self._open_library,
            kind="soft",
            font=self.button_font,
            padx=12,
            pady=5,
        )
        self.open_button.pack(side="right")

        self.reload_button = ThemedButton(
            self.footer,
            text="重新加载题库",
            command=self._reload_library,
            kind="soft",
            font=self.button_font,
            padx=12,
            pady=5,
        )
        self.reload_button.pack(side="right", padx=(0, 8))

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------
    def _apply_theme(self) -> None:
        theme = self.theme
        self.root.configure(bg=theme.bg)
        self.container.configure(bg=theme.bg)

        for frame in (self.header, self.footer):
            frame.configure(bg=theme.bg)
        for child in (self.header.winfo_children() + self.footer.winfo_children()):
            if isinstance(child, tk.Frame):
                child.configure(bg=theme.bg)

        self.title_label.configure(bg=theme.bg, fg=theme.text)
        self.subtitle_label.configure(bg=theme.bg, fg=theme.muted)

        for widget in (self.font_caption,):
            widget.configure(bg=theme.bg, fg=theme.muted)
        self.font_group.configure(bg=theme.bg)
        self.font_value.configure(bg=theme.bg, fg=theme.text)

        self.stats_frame.configure(bg=theme.bg)
        for card in self.stat_cards:
            card.configure(
                bg=theme.surface,
                highlightbackground=theme.border,
                highlightcolor=theme.border,
            )
        for label in self.stat_captions:
            label.configure(bg=theme.surface, fg=theme.muted)
        for index, label in enumerate(self.stat_values):
            label.configure(
                bg=theme.surface,
                fg=theme.accent if index == 0 else theme.text,
            )

        self.sentence_card.configure(
            bg=theme.surface,
            highlightbackground=theme.border,
            highlightcolor=theme.border,
        )
        self.sentence_content.configure(bg=theme.surface)

        self.input_card.configure(bg=theme.surface)
        self.input_title.configure(bg=theme.surface, fg=theme.text)
        self.input_hint.configure(bg=theme.surface, fg=theme.muted)
        self.input_top.configure(bg=theme.surface)
        self.status_label.configure(bg=theme.surface)
        inner = self.input_text.master
        inner.configure(bg=theme.surface)
        self.input_text.configure(
            bg=theme.surface_alt,
            fg=theme.text,
            insertbackground=theme.accent,
            selectbackground=theme.selection,
            selectforeground=theme.text,
        )

        self.footer_hint.configure(bg=theme.bg, fg=theme.muted)

        self.next_button.set_theme(theme)
        self.font_minus.set_theme(theme)
        self.font_plus.set_theme(theme)
        self.reload_button.set_theme(theme)
        self.open_button.set_theme(theme)
        self.theme_toggle.apply_theme(theme, self.theme_key)

        self._set_status(self._status_text, self._status_kind)
        self._apply_input_visuals()
        self._schedule_layout(force=True)

    def _set_theme(self, key: str) -> None:
        if key not in THEMES:
            return
        self.theme_key = key
        self.theme = THEMES[key]
        self._apply_theme()
        self._save_settings()
        self._restore_focus()

    # ------------------------------------------------------------------
    # Font size
    # ------------------------------------------------------------------
    def _change_font(self, delta: int) -> None:
        new_size = self._clamp_font(self.font_px + delta)
        if new_size == self.font_px:
            return
        self.font_px = new_size
        self.font_size_var.set(str(new_size))
        self.cjk_font.configure(size=-new_size)
        self.pinyin_font.configure(size=-self._pinyin_size)
        self.input_text.configure(
            height=2 if self._pinyin_size <= 38 else 3
        )
        self._save_settings()
        self._schedule_layout(force=True)
        self._restore_focus()

    def _on_font_increase(self, _event=None):
        self._change_font(FONT_STEP)
        return "break"

    def _on_font_decrease(self, _event=None):
        self._change_font(-FONT_STEP)
        return "break"

    def _on_mousewheel_font(self, event):
        if event.delta > 0:
            self._change_font(FONT_STEP)
        elif event.delta < 0:
            self._change_font(-FONT_STEP)
        return "break"

    # ------------------------------------------------------------------
    # Sentence bank
    # ------------------------------------------------------------------
    def _load_library(self, initial: bool = False) -> bool:
        try:
            library = load_sentences(SENTENCES_FILE)
        except Exception as exc:
            if initial:
                self._show_library_error(str(exc))
            else:
                messagebox.showerror("题库加载失败", str(exc), parent=self.root)
                self._set_status("题库加载失败，仍保持当前题库。", "error")
            return False

        self.library = library
        self.bag = SentenceBag(library.sentences)
        self.subtitle_label.configure(
            text=f"题库 {library.count} 句 · 一句一句，练出速度"
        )
        self._next_sentence()

        if library.skipped:
            detail = "\n".join(library.skipped[:8])
            if len(library.skipped) > 8:
                detail += f"\n……另有 {len(library.skipped) - 8} 行"
            messagebox.showwarning(
                "部分句子被跳过",
                f"已加载 {library.count} 句，以下内容未载入：\n\n{detail}",
                parent=self.root,
            )
            self._set_status(
                f"已加载 {library.count} 句，跳过 {len(library.skipped)} 行。",
                "info",
            )
        return True

    def _show_library_error(self, message: str) -> None:
        self.subtitle_label.configure(text="题库加载失败")
        self._set_status("无法加载 sentences.txt，请检查文件。", "error")
        if hasattr(self, "input_text"):
            self.input_text.configure(state="disabled")
        messagebox.showerror(
            "无法加载题库",
            f"{message}\n\n请确认 sentences.txt 位于：\n{SENTENCES_FILE}",
            parent=self.root,
        )

    def _reload_library(self) -> None:
        if self._load_library(initial=False):
            self._set_status("题库已重新加载。", "info")
            self._restore_focus()

    def _on_reload_shortcut(self, _event=None):
        self._reload_library()
        return "break"

    def _open_library(self) -> None:
        try:
            os.startfile(str(SENTENCES_FILE))  # type: ignore[attr-defined]
        except OSError as exc:
            messagebox.showerror("无法打开题库", str(exc), parent=self.root)
            return
        self._set_status("已打开题库；保存后点击“重新加载题库”。", "info")

    # ------------------------------------------------------------------
    # Current attempt
    # ------------------------------------------------------------------
    def _next_sentence(self) -> None:
        if self.bag is None:
            return
        try:
            self.sentence = self.bag.next()
        except ValueError:
            return
        self._prepare_attempt("输入第一个字母后开始计时。")

    def _prepare_attempt(self, status: str) -> None:
        self._cancel_tick()
        self.started_at = None
        self.finished_at = None
        self.analysis = analyse(self.sentence, "") if self.sentence else None
        self._set_status(status, "muted")
        self.input_text.configure(state="normal")
        self.input_text.delete("1.0", "end")
        self._apply_input_visuals()
        self._update_stats()
        self._schedule_layout(force=True)
        self._restore_focus()

    def _restart_current(self) -> None:
        if self.sentence is None:
            return
        self._prepare_attempt("已重新开始本句。")

    def _on_restart(self, _event=None):
        self._restart_current()
        return "break"

    def _on_return(self, _event=None):
        if self.analysis is not None and self.analysis.is_complete:
            self._next_sentence()
        elif self.sentence is not None:
            self._set_status("整句输入完成后，按 Enter 进入下一句。", "muted")
        return "break"

    def _restore_focus(self) -> None:
        if self.input_text.cget("state") == "normal":
            self.input_text.focus_set()
        else:
            self.root.focus_set()

    # ------------------------------------------------------------------
    # Typing input
    # ------------------------------------------------------------------
    def _on_key_release(self, _event=None) -> None:
        self._update_attempt()

    def _on_paste(self, _event=None) -> None:
        self.root.after_idle(self._update_attempt)

    def _update_attempt(self) -> None:
        if self.sentence is None:
            return
        if self.input_text.cget("state") == "disabled":
            return

        raw = self.input_text.get("1.0", "end-1c")
        result = analyse(self.sentence, raw)
        self.analysis = result

        if self.started_at is None and result.normalized:
            self.started_at = time.perf_counter()
            self._schedule_tick()

        self._refresh_char_states()
        self._update_stats()
        self._apply_input_visuals()

        if result.is_complete:
            if self.finished_at is None:
                self.finished_at = time.perf_counter()
                self._cancel_tick()
                self._update_stats()
                self.input_text.configure(state="disabled")
                elapsed = self._elapsed()
                self._set_status(
                    f"完成！用时 {elapsed:.1f} 秒，按 Enter 进入下一句。",
                    "done",
                )
            self._restore_focus()
            return

        if result.has_error:
            self._set_status("拼音不匹配，按 Backspace 修改。", "error")
        elif result.normalized:
            self._set_status("输入正确，当前字会自动前进。", "muted")
        elif self.started_at is not None:
            self._set_status("计时中，继续输入即可。", "muted")
        else:
            self._set_status("输入第一个字母后开始计时。", "muted")

    def _apply_input_visuals(self) -> None:
        if not hasattr(self, "input_text"):
            return
        theme = self.theme
        result = self.analysis
        if result is not None and result.is_complete:
            border = theme.done
            foreground = theme.done
        elif result is not None and result.has_error:
            border = theme.error
            foreground = theme.error
        else:
            border = theme.border
            foreground = theme.text

        self.input_card.configure(
            highlightbackground=border, highlightcolor=border
        )
        self.input_text.configure(fg=foreground)
        if result is not None and result.is_complete:
            self.input_text.configure(bg=theme.done_soft)
        elif result is not None and result.has_error:
            self.input_text.configure(bg=theme.error_soft)
        else:
            self.input_text.configure(bg=theme.surface_alt)

    # ------------------------------------------------------------------
    # Timer and stats
    # ------------------------------------------------------------------
    def _schedule_tick(self) -> None:
        if self._tick_job is None:
            self._tick_job = self.root.after(50, self._tick)

    def _cancel_tick(self) -> None:
        if self._tick_job is not None:
            try:
                self.root.after_cancel(self._tick_job)
            except tk.TclError:
                pass
            self._tick_job = None

    def _tick(self) -> None:
        self._tick_job = None
        if self.started_at is not None and self.finished_at is None:
            self._update_stats()
            self._schedule_tick()

    def _elapsed(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.finished_at if self.finished_at is not None else time.perf_counter()
        return max(0.0, end - self.started_at)

    def _update_stats(self) -> None:
        elapsed = self._elapsed()
        self.timer_var.set(format_duration(elapsed))

        completed = self.analysis.completed_chars if self.analysis else 0
        total = self.sentence.han_count if self.sentence else 0
        self.progress_var.set(f"{completed} / {total} 字")

        if self.started_at is None or elapsed < 0.05:
            self.speed_var.set("— 字/分")
        else:
            self.speed_var.set(f"{speed_cpm(completed, elapsed):.1f} 字/分")

    # ------------------------------------------------------------------
    # Sentence rendering
    # ------------------------------------------------------------------
    def _on_sentence_configure(self, event: tk.Event) -> None:
        if abs(event.width - self._last_card_width) < 4:
            return
        self._last_card_width = event.width
        self._schedule_layout()

    def _schedule_layout(self, force: bool = False) -> None:
        if force:
            self._last_card_width = 0
        if self._layout_job is not None:
            try:
                self.root.after_cancel(self._layout_job)
            except tk.TclError:
                pass
        self._layout_job = self.root.after(40, self._layout_sentence)

    def _layout_sentence(self) -> None:
        self._layout_job = None
        for child in self.sentence_content.winfo_children():
            child.destroy()
        self.char_labels = []

        if self.sentence is None:
            label = tk.Label(
                self.sentence_content,
                text="题库中没有可练习的句子",
                font=self.ui_font,
                bg=self.theme.surface,
                fg=self.theme.muted,
            )
            label.pack()
            return

        card_width = self.sentence_card.winfo_width()
        if card_width <= 1:
            card_width = self.root.winfo_width() - 120
        self._last_card_width = card_width
        available = max(320, card_width - 64)

        rows: list[list[tuple[int, object, int]]] = []
        row: list[tuple[int, object, int]] = []
        row_width = 0
        for index, item in enumerate(self.sentence.chars):
            label_width = (
                self.cjk_font.measure(item.char) + 2 * 4 + 2 * 2
            )
            if row and row_width + label_width > available:
                rows.append(row)
                row = []
                row_width = 0
            row.append((index, item, label_width))
            row_width += label_width
        if row:
            rows.append(row)

        for row_items in rows:
            row_frame = tk.Frame(self.sentence_content, bg=self.theme.surface)
            row_frame.pack(anchor="center", pady=2)
            for index, item, _width in row_items:
                label = tk.Label(
                    row_frame,
                    text=item.char,
                    font=self.cjk_font,
                    bg=self.theme.surface,
                    fg=self.theme.faint if not item.is_han else self.theme.text,
                    padx=4,
                    pady=0,
                    bd=0,
                    highlightthickness=2,
                    highlightbackground=self.theme.surface,
                    highlightcolor=self.theme.current_ring,
                )
                label.pack(side="left")
                self.char_labels.append(label)

        self._refresh_char_states()

    def _refresh_char_states(self) -> None:
        if not self.char_labels or self.sentence is None:
            return
        theme = self.theme
        result = self.analysis
        for index, (label, item) in enumerate(
            zip(self.char_labels, self.sentence.chars)
        ):
            if not item.is_han:
                label.configure(
                    bg=theme.surface,
                    fg=theme.faint,
                    highlightbackground=theme.surface,
                )
                continue
            is_done = result is not None and item.end <= result.common_prefix
            is_current = result is not None and result.current_index == index
            if is_current:
                label.configure(
                    bg=theme.current_bg,
                    fg=theme.current_fg,
                    highlightbackground=theme.current_ring,
                )
            elif is_done:
                label.configure(
                    bg=theme.surface,
                    fg=theme.done,
                    highlightbackground=theme.surface,
                )
            else:
                label.configure(
                    bg=theme.surface,
                    fg=theme.text,
                    highlightbackground=theme.surface,
                )

    # ------------------------------------------------------------------
    # Status and shutdown
    # ------------------------------------------------------------------
    def _set_status(self, text: str, kind: str = "muted") -> None:
        self._status_text = text
        self._status_kind = kind
        if not hasattr(self, "status_label"):
            return
        colors = {
            "muted": self.theme.muted,
            "info": self.theme.text,
            "error": self.theme.error,
            "done": self.theme.done,
        }
        self.status_label.configure(text=text, fg=colors.get(kind, self.theme.muted))

    def _on_close(self) -> None:
        self._cancel_tick()
        if self._layout_job is not None:
            try:
                self.root.after_cancel(self._layout_job)
            except tk.TclError:
                pass
            self._layout_job = None
        self._save_settings()
        self.root.destroy()


def run() -> None:
    root = tk.Tk()
    PinyinTrainerApp(root)
    root.mainloop()
