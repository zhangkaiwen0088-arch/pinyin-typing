"""Tkinter interface for the pinyin typing trainer."""

from __future__ import annotations

import json
import os
import time
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime, timedelta
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
    split_typed_chunks,
)
from stats import DailyInputStore, PERIODS, PERIOD_LABELS, StatsStore

APP_DIR = Path(__file__).resolve().parent
SENTENCES_FILE = APP_DIR / "sentences.txt"
SETTINGS_FILE = APP_DIR / ".settings.json"
STATS_FILE = APP_DIR / ".stats.json"
DAILY_FILE = APP_DIR / ".daily.json"

ALL_GROUPS = "全部句子"

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


class SlimScrollbar(tk.Canvas):
    """A narrow, themeable scrollbar used when the sentence overflows."""

    def __init__(self, master: tk.Misc, *, command) -> None:
        super().__init__(
            master,
            width=8,
            bd=0,
            highlightthickness=0,
            takefocus=0,
            cursor="hand2",
        )
        self._command = command
        self._theme: Theme | None = None
        self._first = 0.0
        self._last = 1.0
        self._drag_offset = 0.0
        self.bind("<Configure>", lambda _event: self._redraw())
        self.bind("<Button-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)

    def apply_theme(self, theme: Theme) -> None:
        self._theme = theme
        self.configure(bg=theme.surface)
        self._redraw()

    def set(self, first, last) -> None:
        self._first = max(0.0, min(1.0, float(first)))
        self._last = max(self._first, min(1.0, float(last)))
        self._redraw()

    def _thumb_bounds(self) -> tuple[int, int]:
        height = max(1, self.winfo_height())
        top = int(self._first * height)
        bottom = int(self._last * height)
        if bottom - top < 24:
            bottom = min(height, top + 24)
            top = max(0, bottom - 24)
        return top, bottom

    def _redraw(self) -> None:
        self.delete("all")
        if self._theme is None:
            return
        width = self.winfo_width()
        height = self.winfo_height()
        if width <= 1 or height <= 1:
            return
        self.create_rectangle(
            0, 0, width, height, fill=self._theme.surface, outline=""
        )
        top, bottom = self._thumb_bounds()
        self.create_rectangle(
            2,
            top,
            max(3, width - 2),
            bottom,
            fill=self._theme.faint,
            outline="",
        )

    def _on_press(self, event) -> None:
        top, bottom = self._thumb_bounds()
        if top <= event.y <= bottom:
            self._drag_offset = event.y - top
        else:
            height = max(1, self.winfo_height())
            span = self._last - self._first
            target = max(0.0, min(1.0, event.y / height - span / 2))
            self._command("moveto", target)
            self._drag_offset = span * height / 2

    def _on_drag(self, event) -> None:
        height = max(1, self.winfo_height())
        target = (event.y - self._drag_offset) / height
        self._command("moveto", max(0.0, min(1.0, target)))


class PinyinTrainerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("拼音打字练习")
        self.root.minsize(1040, 760)
        self.root.geometry(self._centred_geometry(1240, 900))
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

        raw_show_pinyin = self.settings.get("show_pinyin", False)
        self.show_pinyin = (
            raw_show_pinyin if isinstance(raw_show_pinyin, bool) else False
        )
        raw_group = self.settings.get("group", ALL_GROUPS)
        self.group_name = (
            raw_group if isinstance(raw_group, str) else ALL_GROUPS
        )
        self.group_options: list[str] = [ALL_GROUPS]

        self.stats_store = StatsStore(STATS_FILE)
        self.daily_store = DailyInputStore(DAILY_FILE)
        self._error_active = False
        self._counted_chars: set[int] = set()
        self._stats_window: StatsWindow | None = None

        self._pick_fonts()

        self.library: SentenceLibrary | None = None
        self.bag: SentenceBag | None = None
        self.sentence: Sentence | None = None
        self.analysis: Analysis | None = None

        self.started_at: float | None = None
        self.finished_at: float | None = None
        self._tick_job: str | None = None
        self._layout_job: str | None = None
        self._last_canvas_width = 0

        self._status_text = "输入第一个字母后开始计时。"
        self._status_kind = "muted"

        self.timer_var = tk.StringVar(value="00:00.0")
        self.progress_var = tk.StringVar(value="0 / 0 字")
        self.speed_var = tk.StringVar(value="— 字/分")
        self.today_input_var = tk.StringVar(
            value=f"{self.daily_store.today_total()} 字"
        )
        self.font_size_var = tk.StringVar(value=str(self.font_px))
        self.group_var = tk.StringVar(value=ALL_GROUPS)
        self.group_button_var = tk.StringVar(value=f"{ALL_GROUPS}  ▾")
        self.hint_var = tk.BooleanVar(value=self.show_pinyin)

        self.char_labels: list[tk.Label] = []
        self.pinyin_labels: list[tk.Label | None] = []

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
        payload = {
            "theme": self.theme_key,
            "font_size": self.font_px,
            "show_pinyin": self.show_pinyin,
            "group": self.group_name,
        }
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
        self.hint_font = tkfont.Font(
            self.root, family=self.mono_family, size=-self._hint_size
        )
        self.separator_font = tkfont.Font(
            self.root, family=self.mono_family, size=-self._separator_size
        )

    @property
    def _pinyin_size(self) -> int:
        return max(20, min(56, round(self.font_px * 0.60)))

    @property
    def _hint_size(self) -> int:
        return max(14, min(34, round(self.font_px * 0.32)))

    @property
    def _separator_size(self) -> int:
        return max(8, round(self._pinyin_size * 0.45))

    def _input_height(self) -> int:
        height = 3 if self._pinyin_size > 38 else 2
        if self.sentence is not None and len(self.sentence.target) > 90:
            height = max(height, 3)
        return height

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
        self._build_filter_bar()
        self._build_stats()
        self._build_footer()
        self._build_input_card()
        self._build_sentence_card()

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

    def _build_filter_bar(self) -> None:
        self.filter_bar = tk.Frame(self.container)
        self.filter_bar.pack(fill="x", pady=(12, 0))

        left = tk.Frame(self.filter_bar)
        left.pack(side="left")
        self.group_caption = tk.Label(
            left, text="练习分组", font=self.small_font
        )
        self.group_caption.pack(side="left", padx=(0, 8))
        self.group_menu = tk.Menubutton(
            left,
            textvariable=self.group_button_var,
            font=self.ui_font,
            width=14,
            anchor="w",
            relief="flat",
            bd=0,
            highlightthickness=1,
            padx=10,
            pady=4,
            cursor="hand2",
            takefocus=0,
            indicatoron=False,
        )
        self.group_popup = tk.Menu(
            self.group_menu, tearoff=False, bd=0
        )
        self.group_menu.configure(menu=self.group_popup)
        self.group_menu.pack(side="left")

        self.hint_check = tk.Checkbutton(
            self.filter_bar,
            text="显示拼音提示",
            variable=self.hint_var,
            command=self._on_hint_toggle,
            font=self.small_font,
            bd=0,
            highlightthickness=0,
            takefocus=0,
            cursor="hand2",
        )
        self.hint_check.pack(side="right")

    def _rebuild_group_menu(self) -> None:
        if not hasattr(self, "group_menu"):
            return
        menu = self.group_popup
        menu.delete(0, "end")
        for name in self.group_options:
            menu.add_command(
                label=name,
                command=lambda selected=name: self._select_group(selected),
            )
        self.group_var.set(self.group_name)
        self.group_button_var.set(f"{self.group_name}  ▾")

    def _build_stats(self) -> None:
        self.stats_frame = tk.Frame(self.container)
        self.stats_frame.pack(fill="x", pady=(14, 0))

        self.stat_cards: list[tk.Frame] = []
        self.stat_captions: list[tk.Label] = []
        self.stat_values: list[tk.Label] = []

        specs = (
            ("计时", self.timer_var),
            ("本句进度", self.progress_var),
            ("速度", self.speed_var),
            ("今日输入", self.today_input_var),
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
        self.sentence_canvas = tk.Canvas(
            self.sentence_card,
            bd=0,
            highlightthickness=0,
            takefocus=0,
        )
        self.sentence_scrollbar = SlimScrollbar(
            self.sentence_card,
            command=self.sentence_canvas.yview,
        )
        self._scrollbar_visible = False
        self.sentence_canvas.configure(
            yscrollcommand=self.sentence_scrollbar.set
        )
        self.sentence_canvas.pack(fill="both", expand=True)
        self.sentence_canvas.bind(
            "<Configure>", self._on_sentence_canvas_configure
        )
        self.sentence_canvas.bind("<MouseWheel>", self._on_sentence_wheel)

        self.sentence_content = tk.Frame(self.sentence_canvas)
        self.sentence_content.bind("<MouseWheel>", self._on_sentence_wheel)
        self._sentence_window = self.sentence_canvas.create_window(
            (0, 0), window=self.sentence_content, anchor="nw"
        )

    def _build_input_card(self) -> None:
        self.input_card = tk.Frame(self.container, highlightthickness=1)
        self.input_card.pack(side="bottom", fill="x", pady=(14, 0))

        self.input_inner = tk.Frame(self.input_card)
        inner = self.input_inner
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
            text="无需声调 · 无需空格 · 自动分字",
            font=self.small_font,
        )
        self.input_hint.pack(side="right")

        self.input_display = tk.Text(
            inner,
            height=2,
            wrap="char",
            font=self.pinyin_font,
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=14,
            pady=10,
            spacing1=1,
            spacing2=1,
            spacing3=1,
            takefocus=0,
            cursor="xterm",
            state="disabled",
        )
        self.input_display.pack(fill="x", pady=(8, 0))
        self.input_display.bind("<Button-1>", self._focus_input_entry)

        # The real editable entry is kept invisible; the display above is a
        # read-only, syllable-grouped rendering of its contents.
        self.input_entry = tk.Entry(
            inner,
            width=1,
            bd=0,
            highlightthickness=0,
            relief="flat",
            insertwidth=0,
            takefocus=0,
            exportselection=False,
        )
        self.input_entry.place(x=0, y=0, width=2, height=2)
        self.input_entry.bind("<KeyRelease>", self._on_key_release)
        self.input_entry.bind("<<Paste>>", self._on_paste)
        self.input_entry.bind("<<Cut>>", self._on_paste)
        self.input_entry.bind("<Return>", self._on_return)
        self.input_entry.bind("<KP_Enter>", self._on_return)
        self.input_entry.bind("<Shift-Return>", self._on_return)
        for sequence in ("<Left>", "<Right>", "<Up>", "<Down>", "<Home>", "<End>", "<Delete>"):
            self.input_entry.bind(sequence, self._block_cursor_move)

        self.status_label = tk.Label(
            inner,
            text=self._status_text,
            font=self.small_font,
            anchor="w",
        )
        self.status_label.pack(fill="x", pady=(7, 0))

        for widget in (
            self.input_card,
            self.input_inner,
            self.input_top,
            self.input_title,
            self.input_hint,
            self.status_label,
        ):
            widget.bind("<Button-1>", self._focus_input_entry, add="+")

    def _build_footer(self) -> None:
        self.footer = tk.Frame(self.container)
        self.footer.pack(side="bottom", fill="x", pady=(12, 0))

        self.footer_hint = tk.Label(
            self.footer,
            text="Backspace 删除   ·   Enter 下一句   ·   Ctrl+R 重开   ·   F5 重载",
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

        self.stats_button = ThemedButton(
            self.footer,
            text="错误统计",
            command=self._open_stats,
            kind="soft",
            font=self.button_font,
            padx=12,
            pady=5,
        )
        self.stats_button.pack(side="right", padx=(0, 8))

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------
    def _apply_theme(self) -> None:
        theme = self.theme
        self.root.configure(bg=theme.bg)
        self.container.configure(bg=theme.bg)

        for frame in (self.header, self.filter_bar, self.footer):
            frame.configure(bg=theme.bg)
        for child in (
            self.header.winfo_children()
            + self.filter_bar.winfo_children()
            + self.footer.winfo_children()
        ):
            if isinstance(child, tk.Frame):
                child.configure(bg=theme.bg)

        self.title_label.configure(bg=theme.bg, fg=theme.text)
        self.subtitle_label.configure(bg=theme.bg, fg=theme.muted)

        for widget in (self.font_caption,):
            widget.configure(bg=theme.bg, fg=theme.muted)
        self.font_group.configure(bg=theme.bg)
        self.font_value.configure(bg=theme.bg, fg=theme.text)

        self.group_caption.configure(bg=theme.bg, fg=theme.muted)
        self.group_menu.configure(
            bg=theme.surface_alt,
            fg=theme.text,
            activebackground=theme.button_hover,
            activeforeground=theme.text,
            highlightbackground=theme.border,
            highlightcolor=theme.border,
        )
        self.group_popup.configure(
            bg=theme.surface,
            fg=theme.text,
            activebackground=theme.accent,
            activeforeground=theme.accent_fg,
            selectcolor=theme.accent_soft,
            font=self.ui_font,
        )
        self.hint_check.configure(
            bg=theme.bg,
            fg=theme.text,
            activebackground=theme.bg,
            activeforeground=theme.text,
            selectcolor=theme.surface_alt,
            disabledforeground=theme.faint,
        )

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
        self.sentence_canvas.configure(bg=theme.surface)
        self.sentence_scrollbar.apply_theme(theme)
        self.sentence_content.configure(bg=theme.surface)

        self.input_card.configure(bg=theme.surface)
        self.input_title.configure(bg=theme.surface, fg=theme.text)
        self.input_hint.configure(bg=theme.surface, fg=theme.muted)
        self.input_top.configure(bg=theme.surface)
        self.status_label.configure(bg=theme.surface)
        inner = self.input_display.master
        inner.configure(bg=theme.surface)
        self.input_display.configure(
            bg=theme.surface_alt,
            fg=theme.text,
        )
        self.input_entry.configure(
            bg=theme.surface_alt,
            fg=theme.surface_alt,
            insertbackground=theme.surface_alt,
            selectbackground=theme.surface_alt,
            selectforeground=theme.surface_alt,
        )

        self.footer_hint.configure(bg=theme.bg, fg=theme.muted)

        self.next_button.set_theme(theme)
        self.font_minus.set_theme(theme)
        self.font_plus.set_theme(theme)
        self.reload_button.set_theme(theme)
        self.open_button.set_theme(theme)
        self.stats_button.set_theme(theme)
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
        self.hint_font.configure(size=-self._hint_size)
        self.separator_font.configure(size=-self._separator_size)
        self.input_display.configure(
            height=self._input_height()
        )
        self._render_input_display()
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
        self.group_options = [ALL_GROUPS, *library.groups]
        if self.group_name not in self.group_options:
            self.group_name = ALL_GROUPS
        self.group_var.set(self.group_name)
        self._rebuild_group_menu()
        self.group_menu.configure(state="normal")
        self._start_group()

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

    def _filtered_sentences(self) -> list[Sentence]:
        if self.library is None:
            return []
        if self.group_name == ALL_GROUPS:
            return list(self.library.sentences)
        return [
            sentence
            for sentence in self.library.sentences
            if sentence.group == self.group_name
        ]

    def _update_subtitle(self) -> None:
        if self.library is None:
            return
        count = len(self._filtered_sentences())
        if self.group_name == ALL_GROUPS:
            self.subtitle_label.configure(
                text=f"题库 {self.library.count} 句 · 全部句子"
            )
        else:
            self.subtitle_label.configure(
                text=f"题库 {self.library.count} 句 · {self.group_name} {count} 句"
            )

    def _start_group(self) -> None:
        sentences = self._filtered_sentences()
        if not sentences:
            self.bag = None
            self._set_status("当前分组没有可用句子。", "error")
            return
        self.bag = SentenceBag(sentences)
        self._update_subtitle()
        self._next_sentence()

    def _select_group(self, selected: str) -> None:
        if selected not in self.group_options:
            return
        if selected == self.group_name and self.sentence is not None:
            self.group_var.set(selected)
            self.group_button_var.set(f"{selected}  ▾")
            return
        self.group_name = selected
        self.group_var.set(selected)
        self.group_button_var.set(f"{selected}  ▾")
        self._save_settings()
        self._start_group()
        self._set_status(f"已切换到：{selected}", "info")
        self._restore_focus()

    def _on_hint_toggle(self) -> None:
        self.show_pinyin = bool(self.hint_var.get())
        self._error_active = bool(
            self.analysis is not None and self.analysis.has_error
        )
        self._save_settings()
        self._schedule_layout(force=True)
        if self.show_pinyin:
            self._set_status("已显示拼音提示；错字统计暂停记录。", "info")
        else:
            self._set_status("已关闭拼音提示；之后的错字会记录到统计。", "info")
        self._restore_focus()

    def _show_library_error(self, message: str) -> None:
        self.subtitle_label.configure(text="题库加载失败")
        self._set_status("无法加载 sentences.txt，请检查文件。", "error")
        if hasattr(self, "input_entry"):
            self.input_entry.configure(state="disabled")
        if hasattr(self, "group_menu"):
            self.group_menu.configure(state="disabled")
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

    def _open_stats(self) -> None:
        if self._stats_window is not None:
            try:
                if self._stats_window.winfo_exists():
                    self._stats_window.lift()
                    self._stats_window.focus_set()
                    return
            except tk.TclError:
                pass
            self._stats_window = None
        self._stats_window = StatsWindow(self)

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
        self._error_active = False
        self._counted_chars = set()
        self.analysis = analyse(self.sentence, "") if self.sentence else None
        self._set_status(status, "muted")
        self.input_entry.configure(state="normal")
        self.input_entry.delete(0, "end")
        self.input_entry.icursor("end")
        self.input_display.configure(height=self._input_height())
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
        if self.input_entry.cget("state") == "normal":
            self.input_entry.focus_set()
            self.input_entry.icursor("end")
        else:
            self.root.focus_set()

    def _focus_input_entry(self, _event=None):
        if self.input_entry.cget("state") == "normal":
            self.input_entry.focus_set()
            self.input_entry.icursor("end")
        return "break"

    @staticmethod
    def _block_cursor_move(_event=None):
        return "break"

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
        if self.input_entry.cget("state") == "disabled":
            return

        raw = self.input_entry.get()
        self.input_entry.icursor("end")
        result = analyse(self.sentence, raw)
        self.analysis = result

        # Keep the invisible input buffer to letters only.  Users never need
        # to type spaces, and this avoids an invisible space consuming a
        # Backspace press.
        if raw != result.normalized:
            self.input_entry.delete(0, "end")
            self.input_entry.insert(0, result.normalized)
            self.input_entry.icursor("end")

        if self.started_at is None and result.normalized:
            self.started_at = time.perf_counter()
            self._schedule_tick()

        if result.has_error:
            if (
                not self.show_pinyin
                and not self._error_active
                and result.current_index is not None
            ):
                item = self.sentence.chars[result.current_index]
                self.stats_store.record(
                    char=item.char,
                    target=item.pinyin,
                    typed=result.normalized,
                    sentence=self.sentence.text,
                )
            self._error_active = True
        else:
            self._error_active = False

        self._record_completed_chars(result)
        self._refresh_char_states()
        self._update_stats()
        self._apply_input_visuals()

        if result.is_complete:
            if self.finished_at is None:
                self.finished_at = time.perf_counter()
                self._cancel_tick()
                self._update_stats()
                self.input_entry.configure(state="disabled")
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
        if not hasattr(self, "input_display"):
            return
        theme = self.theme
        result = self.analysis
        if result is not None and result.is_complete:
            border = theme.done
        elif result is not None and result.has_error:
            border = theme.error
        else:
            border = theme.border

        self.input_card.configure(
            highlightbackground=border, highlightcolor=border
        )
        self._render_input_display()

    def _record_completed_chars(self, result: Analysis) -> None:
        if self.sentence is None:
            return
        newly_completed = 0
        for index, item in enumerate(self.sentence.chars):
            if not item.is_han or item.end > result.common_prefix:
                continue
            if index in self._counted_chars:
                continue
            self._counted_chars.add(index)
            newly_completed += 1
        if newly_completed:
            self.daily_store.add(newly_completed)
            self.today_input_var.set(
                f"{self.daily_store.today_total()} 字"
            )

    def _render_input_display(self) -> None:
        if not hasattr(self, "input_display"):
            return
        theme = self.theme
        display = self.input_display
        result = self.analysis
        if result is not None and result.is_complete:
            background = theme.done_soft
        elif result is not None and result.has_error:
            background = theme.error_soft
        else:
            background = theme.surface_alt

        display.configure(state="normal", bg=background, fg=theme.text)
        display.delete("1.0", "end")
        display.tag_configure("done", foreground=theme.done)
        display.tag_configure("current", foreground=theme.text)
        display.tag_configure("error", foreground=theme.error)
        display.tag_configure(
            "sep", foreground=theme.faint, font=self.separator_font
        )
        display.tag_configure("caret", foreground=theme.accent)

        chunks = (
            split_typed_chunks(self.sentence, result.normalized)
            if self.sentence is not None and result is not None
            else ()
        )
        for index, chunk in enumerate(chunks):
            if index:
                display.insert("end", " ", "sep")
            if result is not None and result.is_complete:
                tag = "done"
            elif chunk.char_index is None:
                tag = "error"
            else:
                item = self.sentence.chars[chunk.char_index]
                if result is not None and item.end <= result.common_prefix:
                    tag = "done"
                elif result is not None and result.has_error:
                    tag = "error"
                else:
                    tag = "current"
            display.insert("end", chunk.text, tag)

        if result is None or not result.is_complete:
            if chunks:
                display.insert("end", " ", "sep")
            display.insert("end", "|", "caret")

        display.see("end")
        display.configure(state="disabled")
        self.input_entry.configure(
            bg=theme.surface,
            fg=theme.surface,
            insertbackground=theme.surface,
            selectbackground=theme.surface,
            selectforeground=theme.surface,
        )

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
    def _on_sentence_canvas_configure(self, event: tk.Event) -> None:
        if abs(event.width - self._last_canvas_width) >= 4:
            self._last_canvas_width = event.width
            self._schedule_layout()
        else:
            self._update_sentence_geometry()

    def _on_sentence_wheel(self, event):
        if event.state & 0x0004:  # Ctrl+wheel is reserved for font size.
            return None
        step = -1 if event.delta > 0 else 1
        self.sentence_canvas.yview_scroll(step, "units")
        return "break"

    def _update_sentence_geometry(self) -> None:
        if not hasattr(self, "sentence_canvas"):
            return
        canvas_width = self.sentence_canvas.winfo_width()
        canvas_height = self.sentence_canvas.winfo_height()
        if canvas_width <= 1 or canvas_height <= 1:
            # The <Configure> event will call us again once the canvas is
            # mapped.  Never self-reschedule here: update() would never return.
            return

        self.sentence_content.update_idletasks()
        content_height = self.sentence_content.winfo_reqheight()
        self.sentence_canvas.itemconfigure(
            self._sentence_window, width=canvas_width
        )
        needs_scrollbar = content_height + 40 > canvas_height
        if needs_scrollbar:
            if not self._scrollbar_visible:
                self.sentence_scrollbar.place(
                    relx=1.0,
                    y=0,
                    anchor="ne",
                    relheight=1.0,
                    width=8,
                )
                self._scrollbar_visible = True
            y = 20
            scroll_height = content_height + 40
        else:
            if self._scrollbar_visible:
                self.sentence_scrollbar.place_forget()
                self._scrollbar_visible = False
            y = max(20, (canvas_height - content_height) // 2)
            scroll_height = canvas_height
            self.sentence_canvas.yview_moveto(0)
        self.sentence_canvas.coords(self._sentence_window, 0, y)
        self.sentence_canvas.configure(
            scrollregion=(0, 0, canvas_width, scroll_height)
        )
        if self._scrollbar_visible:
            self.sentence_scrollbar.set(*self.sentence_canvas.yview())

    def _schedule_layout(self, force: bool = False) -> None:
        if force:
            self._last_canvas_width = 0
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
        self.pinyin_labels = []

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

        canvas_width = self.sentence_canvas.winfo_width()
        if canvas_width <= 1:
            canvas_width = self.root.winfo_width() - 160
        self._last_canvas_width = canvas_width
        available = max(320, canvas_width - 64)

        rows: list[list[tuple[int, object, int]]] = []
        row: list[tuple[int, object, int]] = []
        row_width = 0
        for index, item in enumerate(self.sentence.chars):
            char_width = self.cjk_font.measure(item.char) + 2 * 4 + 2 * 2
            cell_width = char_width
            if self.show_pinyin:
                hint_text = item.pinyin if item.is_han else " "
                hint_width = self.hint_font.measure(hint_text) + 2 * 4
                cell_width = max(char_width, hint_width)
            if row and row_width + cell_width > available:
                rows.append(row)
                row = []
                row_width = 0
            row.append((index, item, cell_width))
            row_width += cell_width
        if row:
            rows.append(row)

        for row_items in rows:
            row_frame = tk.Frame(self.sentence_content, bg=self.theme.surface)
            row_frame.pack(anchor="center", pady=2)
            row_frame.bind("<MouseWheel>", self._on_sentence_wheel)
            for index, item, _width in row_items:
                cell = tk.Frame(row_frame, bg=self.theme.surface)
                cell.pack(side="left")
                cell.bind("<MouseWheel>", self._on_sentence_wheel)

                if self.show_pinyin:
                    hint = tk.Label(
                        cell,
                        text=item.pinyin if item.is_han else " ",
                        font=self.hint_font,
                        bg=self.theme.surface,
                        fg=self.theme.muted,
                        padx=4,
                        pady=0,
                        bd=0,
                    )
                    hint.pack(anchor="center")
                    hint.bind("<MouseWheel>", self._on_sentence_wheel)
                    self.pinyin_labels.append(hint)
                else:
                    self.pinyin_labels.append(None)

                label = tk.Label(
                    cell,
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
                label.pack(anchor="center")
                label.bind("<MouseWheel>", self._on_sentence_wheel)
                self.char_labels.append(label)

        self._refresh_char_states()
        self._update_sentence_geometry()
        self.sentence_canvas.yview_moveto(0)

    def _refresh_char_states(self) -> None:
        if not self.char_labels or self.sentence is None:
            return
        theme = self.theme
        result = self.analysis
        for index, (label, item) in enumerate(
            zip(self.char_labels, self.sentence.chars)
        ):
            hint = (
                self.pinyin_labels[index]
                if index < len(self.pinyin_labels)
                else None
            )
            if not item.is_han:
                label.configure(
                    bg=theme.surface,
                    fg=theme.faint,
                    highlightbackground=theme.surface,
                )
                if hint is not None:
                    hint.configure(fg=theme.faint)
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
            if hint is not None:
                if is_current:
                    hint.configure(fg=theme.accent)
                elif is_done:
                    hint.configure(fg=theme.done)
                else:
                    hint.configure(fg=theme.muted)

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


class StatsWindow(tk.Toplevel):
    """Modal three-period view of the most frequently mistyped Hanzi."""

    def __init__(self, app: PinyinTrainerApp) -> None:
        super().__init__(app.root)
        self.app = app
        self.theme = app.theme
        self.period = "today"
        self._table_scroll_visible = False
        self.title("错字统计")
        self.configure(bg=self.theme.bg)
        self.transient(app.root)
        self.minsize(920, 600)

        width, height = 1080, 720
        self.update_idletasks()
        x = app.root.winfo_rootx() + max(
            0, (app.root.winfo_width() - width) // 2
        )
        y = app.root.winfo_rooty() + max(
            0, (app.root.winfo_height() - height) // 2
        )
        self.geometry(f"{width}x{height}+{x}+{y}")

        self._pick_fonts()
        self._build()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda _event: self.close())
        self.grab_set()
        self.focus_set()

    def _pick_fonts(self) -> None:
        self.heading_font = tkfont.Font(
            self, family=self.app.cjk_family, size=-26, weight="bold"
        )
        self.period_font = tkfont.Font(
            self, family=self.app.cjk_family, size=-18, weight="bold"
        )
        self.char_font = tkfont.Font(
            self, family=self.app.cjk_family, size=-26
        )
        self.body_font = tkfont.Font(
            self, family=self.app.cjk_family, size=-13
        )
        self.small_font = tkfont.Font(
            self, family=self.app.cjk_family, size=-11
        )
        self.count_font = tkfont.Font(
            self, family=self.app.mono_family, size=-15, weight="bold"
        )
        self.pinyin_font = tkfont.Font(
            self, family=self.app.mono_family, size=-16, weight="bold"
        )
        self.button_font = tkfont.Font(
            self, family=self.app.cjk_family, size=-13
        )

    def _build(self) -> None:
        theme = self.theme
        container = tk.Frame(self, bg=theme.bg)
        container.pack(fill="both", expand=True, padx=24, pady=20)

        header = tk.Frame(container, bg=theme.bg)
        header.pack(fill="x")
        title = tk.Label(
            header,
            text="错字统计",
            font=self.heading_font,
            bg=theme.bg,
            fg=theme.text,
        )
        title.pack(side="left")
        close_button = ThemedButton(
            header,
            text="关闭",
            command=self.close,
            kind="soft",
            font=self.button_font,
            padx=14,
            pady=5,
        )
        close_button.pack(side="right")
        close_button.set_theme(theme)

        subtitle = tk.Label(
            container,
            text="只统计未显示拼音提示时的打错汉字 · 本周从周一开始",
            font=self.small_font,
            bg=theme.bg,
            fg=theme.muted,
        )
        subtitle.pack(anchor="w", pady=(4, 0))

        toolbar = tk.Frame(container, bg=theme.bg)
        toolbar.pack(fill="x", pady=(12, 0))
        caption = tk.Label(
            toolbar,
            text="查看范围",
            font=self.small_font,
            bg=theme.bg,
            fg=theme.muted,
        )
        caption.pack(side="left", padx=(0, 8))

        self.period_buttons: dict[str, ThemedButton] = {}
        for period in PERIODS:
            button = ThemedButton(
                toolbar,
                text=PERIOD_LABELS[period],
                command=lambda selected=period: self._select_period(selected),
                kind="segment",
                font=self.button_font,
                padx=16,
                pady=5,
            )
            button.pack(side="left", padx=2)
            self.period_buttons[period] = button

        self.summary_label = tk.Label(
            container,
            text="",
            font=self.small_font,
            bg=theme.bg,
            fg=theme.muted,
        )
        self.summary_label.pack(anchor="w", pady=(8, 0))

        self.table_card = tk.Frame(
            container,
            bg=theme.surface,
            highlightthickness=1,
            highlightbackground=theme.border,
            highlightcolor=theme.border,
        )
        self.table_card.pack(fill="both", expand=True, pady=(10, 0))

        header = tk.Frame(self.table_card, bg=theme.surface_alt)
        header.pack(fill="x")
        header.grid_columnconfigure(2, weight=1)
        for column, text, width in (
            (0, "拼音", 12),
            (1, "错误次数", 8),
            (2, "汉字（按次数排序）", 0),
            (3, "最后出错", 14),
        ):
            label = tk.Label(
                header,
                text=text,
                font=self.small_font,
                bg=theme.surface_alt,
                fg=theme.muted,
                anchor="w",
                width=width if width else 0,
            )
            label.grid(
                row=0,
                column=column,
                sticky="ew" if column == 2 else "w",
                padx=(14 if column == 0 else 4, 8),
                pady=8,
            )

        self.table_holder = tk.Frame(self.table_card, bg=theme.surface)
        self.table_holder.pack(fill="both", expand=True)
        self.table_canvas = tk.Canvas(
            self.table_holder,
            bg=theme.surface,
            bd=0,
            highlightthickness=0,
            takefocus=0,
        )
        self.table_canvas.pack(fill="both", expand=True)
        self.table_scrollbar = SlimScrollbar(
            self.table_holder,
            command=self.table_canvas.yview,
        )
        self.table_scrollbar.apply_theme(theme)
        self.table_canvas.configure(
            yscrollcommand=self.table_scrollbar.set
        )
        self.table_body = tk.Frame(self.table_canvas, bg=theme.surface)
        self._table_window = self.table_canvas.create_window(
            (0, 0), window=self.table_body, anchor="nw"
        )
        self.table_body.bind("<MouseWheel>", self._on_table_wheel)
        self.table_canvas.bind("<Configure>", self._on_table_canvas_configure)
        self.table_canvas.bind("<MouseWheel>", self._on_table_wheel)
        self._char_labels: list[tk.Label] = []

        footer = tk.Frame(container, bg=theme.bg)
        footer.pack(fill="x", pady=(12, 0))
        note = tk.Label(
            footer,
            text="只统计关闭拼音提示时的错误 · 全部显示 · 本周从周一开始",
            font=self.small_font,
            bg=theme.bg,
            fg=theme.muted,
        )
        note.pack(side="left")
        clear_button = ThemedButton(
            footer,
            text="清空统计",
            command=self._clear,
            kind="soft",
            font=self.button_font,
            padx=12,
            pady=5,
        )
        clear_button.pack(side="right")
        clear_button.set_theme(theme)

        self._refresh_table()

    def _select_period(self, period: str) -> None:
        if period not in PERIODS:
            return
        self.period = period
        self._refresh_table()

    def _refresh_table(self) -> None:
        theme = self.theme
        now = datetime.now().astimezone()
        summary = self.app.stats_store.summary_by_pinyin(self.period, now)

        for period, button in self.period_buttons.items():
            button.set_theme(theme, selected=(period == self.period))

        range_text = self._period_range(self.period, now)
        self.summary_label.configure(
            text=f"{range_text} · 共 {summary.total} 次错误 · {len(summary.items)} 个拼音"
        )

        for child in self.table_body.winfo_children():
            child.destroy()
        self._char_labels = []

        if not summary.items:
            empty = tk.Label(
                self.table_body,
                text="当前时间范围内没有打错记录",
                font=self.body_font,
                bg=theme.surface,
                fg=theme.faint,
            )
            empty.pack(pady=36)
            self.table_body.update_idletasks()
            self._update_table_geometry()
            return

        for index, item in enumerate(summary.items):
            background = theme.surface if index % 2 == 0 else theme.surface_alt
            row = tk.Frame(self.table_body, bg=background)
            row.pack(fill="x")
            row.grid_columnconfigure(2, weight=1)
            row.bind("<MouseWheel>", self._on_table_wheel)

            pinyin_label = tk.Label(
                row,
                text=item.pinyin,
                font=self.pinyin_font,
                bg=background,
                fg=theme.accent,
                anchor="w",
                width=12,
            )
            pinyin_label.grid(
                row=0, column=0, sticky="w", padx=(14, 4), pady=6
            )
            count_label = tk.Label(
                row,
                text=str(item.count),
                font=self.count_font,
                bg=background,
                fg=theme.text,
                anchor="w",
                width=8,
            )
            count_label.grid(row=0, column=1, sticky="w", padx=(4, 8), pady=6)

            chars_text = "   ".join(
                f"{char.char}×{char.count}" for char in item.chars
            )
            chars_label = tk.Label(
                row,
                text=chars_text,
                font=self.body_font,
                bg=background,
                fg=theme.text,
                anchor="w",
                justify="left",
                wraplength=520,
            )
            chars_label.grid(
                row=0, column=2, sticky="ew", padx=(4, 8), pady=6
            )
            self._char_labels.append(chars_label)

            last_label = tk.Label(
                row,
                text=self._last_time(item.last_at, now),
                font=self.small_font,
                bg=background,
                fg=theme.muted,
                anchor="w",
                width=14,
            )
            last_label.grid(
                row=0, column=3, sticky="w", padx=(4, 14), pady=6
            )

            for widget in (pinyin_label, count_label, chars_label, last_label):
                widget.bind("<MouseWheel>", self._on_table_wheel)

        self.table_body.update_idletasks()
        self._update_char_wrap()
        self._update_table_geometry()
        self.table_canvas.yview_moveto(0)

    def _update_char_wrap(self) -> None:
        width = max(300, self.table_canvas.winfo_width() - 390)
        for label in self._char_labels:
            label.configure(wraplength=width)

    def _on_table_canvas_configure(self, event: tk.Event) -> None:
        self.table_canvas.itemconfigure(self._table_window, width=event.width)
        self._update_char_wrap()
        self._update_table_geometry()

    def _update_table_geometry(self) -> None:
        canvas_width = self.table_canvas.winfo_width()
        canvas_height = self.table_canvas.winfo_height()
        if canvas_width <= 1 or canvas_height <= 1:
            return
        self.table_body.update_idletasks()
        body_height = self.table_body.winfo_reqheight()
        self.table_canvas.itemconfigure(
            self._table_window, width=canvas_width
        )
        if body_height > canvas_height:
            if not self._table_scroll_visible:
                self.table_scrollbar.place(
                    relx=1.0,
                    y=0,
                    anchor="ne",
                    relheight=1.0,
                    width=8,
                )
                self._table_scroll_visible = True
            self.table_canvas.configure(
                scrollregion=(0, 0, canvas_width, body_height)
            )
        else:
            if self._table_scroll_visible:
                self.table_scrollbar.place_forget()
                self._table_scroll_visible = False
            self.table_canvas.configure(
                scrollregion=(0, 0, canvas_width, canvas_height)
            )
            self.table_canvas.yview_moveto(0)
        if self._table_scroll_visible:
            self.table_scrollbar.set(*self.table_canvas.yview())

    def _on_table_wheel(self, event):
        if event.state & 0x0004:
            return None
        step = -1 if event.delta > 0 else 1
        self.table_canvas.yview_scroll(step, "units")
        return "break"

    @staticmethod
    def _period_range(period: str, now: datetime) -> str:
        if period == "today":
            return now.strftime("%Y-%m-%d")
        if period == "week":
            start = now - timedelta(days=now.weekday())
            return f"{start:%m-%d} 至 {now:%m-%d}"
        return now.strftime("%Y 年 %m 月")

    @staticmethod
    def _last_time(at: datetime, now: datetime) -> str:
        local = at.astimezone(now.tzinfo)
        if local.date() == now.date():
            return local.strftime("最后 %H:%M")
        return local.strftime("最后 %m-%d %H:%M")

    def _clear(self) -> None:
        if not messagebox.askyesno(
            "清空统计",
            "确定清空所有错字记录吗？此操作不可撤销。",
            parent=self,
        ):
            return
        self.app.stats_store.clear()
        self._refresh_table()
        self.app._set_status("错字统计已清空。", "info")

    def close(self) -> None:
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.app._stats_window = None
        self.destroy()
        self.app._restore_focus()


def run() -> None:
    root = tk.Tk()
    PinyinTrainerApp(root)
    root.mainloop()
