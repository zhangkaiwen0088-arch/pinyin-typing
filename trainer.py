"""Core pinyin-typing logic.

The GUI is deliberately kept out of this module so that sentence parsing,
input matching and sentence selection can be tested without Tk.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from pypinyin import Style, pinyin

HAN_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
LATIN_ONLY = re.compile(r"[^a-z]")


def is_han(char: str) -> bool:
    """Return True for a single Han character."""
    return bool(HAN_PATTERN.fullmatch(char))


def _clean_syllable(value: str) -> str:
    value = value.strip().lower().replace("ü", "v").replace("u:", "v")
    return LATIN_ONLY.sub("", value)


def normalize_input(raw: str) -> str:
    """Normalise typed pinyin for comparison.

    Case, whitespace, punctuation and apostrophes are ignored.  Users may
    type ``ü`` (or ``u:``) and it will be treated as ``v``, which is the
    spelling pypinyin uses for syllables such as ``lv`` and ``nv``.
    """
    lowered = raw.lower().replace("ü", "v").replace("u:", "v")
    return "".join(char for char in lowered if "a" <= char <= "z")


@dataclass(frozen=True, slots=True)
class SentenceChar:
    """One displayed character and its position in the concatenated pinyin."""

    char: str
    pinyin: str
    start: int
    end: int
    is_han: bool


@dataclass(frozen=True, slots=True)
class Sentence:
    """A sentence plus the exact pinyin string the user must type."""

    text: str
    chars: tuple[SentenceChar, ...]
    target: str
    han_count: int

    @classmethod
    def from_text(cls, text: str) -> "Sentence":
        text = text.strip()
        if not text:
            raise ValueError("句子为空")

        # Passing the whole sentence (rather than one character at a time)
        # lets pypinyin use its phrase dictionary for 多音字 such as 银行/音乐.
        readings = pinyin(text, style=Style.NORMAL, heteronym=False)
        if len(readings) != len(text):
            raise ValueError("拼音解析结果与句子长度不一致")

        chars: list[SentenceChar] = []
        target_parts: list[str] = []
        offset = 0
        han_count = 0

        for char, result in zip(text, readings):
            if not is_han(char):
                chars.append(SentenceChar(char, "", offset, offset, False))
                continue

            if not result:
                raise ValueError(f"无法生成“{char}”的拼音")

            syllable = _clean_syllable(str(result[0]))
            if not syllable:
                raise ValueError(f"“{char}”的拼音为空")

            start = offset
            offset += len(syllable)
            target_parts.append(syllable)
            chars.append(SentenceChar(char, syllable, start, offset, True))
            han_count += 1

        target = "".join(target_parts)
        if not target or han_count == 0:
            raise ValueError("句子中没有可练习的汉字")

        return cls(text=text, chars=tuple(chars), target=target, han_count=han_count)

    @property
    def char_count(self) -> int:
        return self.han_count


@dataclass(frozen=True, slots=True)
class Analysis:
    """Result of comparing the current input with a sentence's target."""

    raw_input: str
    normalized: str
    target: str
    common_prefix: int
    completed_chars: int
    current_index: int | None
    is_complete: bool
    is_prefix: bool
    has_error: bool

    @property
    def progress(self) -> float:
        total = len(self.target)
        return min(1.0, self.common_prefix / total) if total else 0.0


def analyse(sentence: Sentence, raw_input: str) -> Analysis:
    normalized = normalize_input(raw_input)
    target = sentence.target

    limit = min(len(normalized), len(target))
    prefix = 0
    while prefix < limit and normalized[prefix] == target[prefix]:
        prefix += 1

    completed = sum(
        1 for item in sentence.chars if item.is_han and item.end <= prefix
    )
    current_index = next(
        (
            index
            for index, item in enumerate(sentence.chars)
            if item.is_han and item.end > prefix
        ),
        None,
    )
    is_prefix = target.startswith(normalized)

    return Analysis(
        raw_input=raw_input,
        normalized=normalized,
        target=target,
        common_prefix=prefix,
        completed_chars=completed,
        current_index=current_index,
        is_complete=normalized == target,
        is_prefix=is_prefix,
        has_error=not is_prefix,
    )


def format_duration(seconds: float) -> str:
    """Format seconds as mm:ss.d (tenths)."""
    total_tenths = max(0, int(round(seconds * 10)))
    minutes, remainder = divmod(total_tenths, 600)
    whole_seconds, tenths = divmod(remainder, 10)
    return f"{minutes:02d}:{whole_seconds:02d}.{tenths}"


def speed_cpm(char_count: int, seconds: float) -> float:
    """Characters per minute."""
    if seconds <= 0:
        return 0.0
    return char_count * 60.0 / seconds


class SentenceBag:
    """Shuffle-bag randomiser that avoids an immediate repeat across refills."""

    def __init__(
        self,
        sentences: Sequence[Sentence],
        rng: random.Random | None = None,
    ) -> None:
        self._rng = rng or random.Random()
        self._sentences: list[Sentence] = []
        self._bag: list[Sentence] = []
        self._last: Sentence | None = None
        self.reset(sentences)

    @property
    def size(self) -> int:
        return len(self._sentences)

    def reset(self, sentences: Sequence[Sentence]) -> None:
        if not sentences:
            raise ValueError("题库为空")
        self._sentences = list(sentences)
        self._bag = []
        self._last = None

    def next(self) -> Sentence:
        if not self._bag:
            self._bag = list(self._sentences)
            self._rng.shuffle(self._bag)
            if (
                len(self._bag) > 1
                and self._last is not None
                and self._bag[-1] == self._last
            ):
                self._bag[0], self._bag[-1] = self._bag[-1], self._bag[0]

        sentence = self._bag.pop()
        self._last = sentence
        return sentence


@dataclass(frozen=True, slots=True)
class SentenceLibrary:
    sentences: tuple[Sentence, ...]
    skipped: tuple[str, ...]
    source: Path

    @property
    def count(self) -> int:
        return len(self.sentences)


def load_sentences(path: str | Path) -> SentenceLibrary:
    """Read the UTF-8 sentence bank.

    One sentence per line; blank lines and lines whose first non-space
    character is ``#`` are comments.  Invalid or duplicate lines are skipped
    and reported in ``SentenceLibrary.skipped``.
    """
    source = Path(path)
    try:
        content = source.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("题库必须使用 UTF-8 编码保存。") from exc

    sentences: list[Sentence] = []
    skipped: list[str] = []
    seen: set[str] = set()

    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            sentence = Sentence.from_text(line)
        except Exception as exc:  # A single bad line must not break the bank.
            skipped.append(f"第 {line_number} 行：{exc}")
            continue
        if sentence.text in seen:
            skipped.append(f"第 {line_number} 行：重复句子，已忽略")
            continue
        seen.add(sentence.text)
        sentences.append(sentence)

    if not sentences:
        raise ValueError(f"题库中没有有效句子：{source}")

    return SentenceLibrary(
        sentences=tuple(sentences),
        skipped=tuple(skipped),
        source=source.resolve(),
    )
