"""Persistent mistyped-Hanzi statistics.

The data is deliberately stored as a small JSON file next to the project so
users can inspect or delete it.  No sentence text or keystrokes are sent
anywhere.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

PERIODS = ("today", "week", "month")
PERIOD_LABELS = {"today": "今天", "week": "本周", "month": "本月"}


@dataclass(frozen=True, slots=True)
class ErrorEvent:
    at: datetime
    char: str
    target: str
    typed: str
    sentence: str

    def to_dict(self) -> dict[str, str]:
        return {
            "at": self.at.isoformat(timespec="seconds"),
            "char": self.char,
            "target": self.target,
            "typed": self.typed,
            "sentence": self.sentence,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ErrorEvent":
        at = datetime.fromisoformat(str(data["at"]))
        if at.tzinfo is None:
            at = at.astimezone()
        char = str(data["char"]).strip()
        if not char:
            raise ValueError("empty character")
        return cls(
            at=at,
            char=char,
            target=str(data.get("target", "")),
            typed=str(data.get("typed", "")),
            sentence=str(data.get("sentence", "")),
        )


@dataclass(frozen=True, slots=True)
class HanziStat:
    char: str
    count: int
    last_at: datetime


@dataclass(frozen=True, slots=True)
class PeriodSummary:
    period: str
    total: int
    items: tuple[HanziStat, ...]


@dataclass(frozen=True, slots=True)
class PinyinStat:
    pinyin: str
    count: int
    last_at: datetime
    chars: tuple[HanziStat, ...]


@dataclass(frozen=True, slots=True)
class PinyinPeriodSummary:
    period: str
    total: int
    items: tuple[PinyinStat, ...]


class StatsStore:
    """Load, append and aggregate error events."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._events: list[ErrorEvent] = []
        self._load()

    @property
    def events(self) -> tuple[ErrorEvent, ...]:
        return tuple(self._events)

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return

        rows = raw.get("errors", []) if isinstance(raw, dict) else raw
        if not isinstance(rows, list):
            return
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                self._events.append(ErrorEvent.from_dict(row))
            except (KeyError, TypeError, ValueError):
                continue

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "errors": [event.to_dict() for event in self._events],
        }
        temporary = self.path.with_name(self.path.name + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def record(
        self,
        *,
        char: str,
        target: str,
        typed: str,
        sentence: str,
        when: datetime | None = None,
    ) -> bool:
        at = when or datetime.now().astimezone()
        if at.tzinfo is None:
            at = at.astimezone()
        self._events.append(
            ErrorEvent(
                at=at,
                char=char,
                target=target,
                typed=typed,
                sentence=sentence,
            )
        )
        try:
            self._save()
        except OSError:
            # A read-only project folder should never break typing practice.
            return False
        return True

    def clear(self) -> None:
        self._events.clear()
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass

    @staticmethod
    def _period_start(period: str, current: datetime) -> datetime:
        if period not in PERIODS:
            raise ValueError(f"unknown period: {period}")
        if period == "today":
            return current.replace(hour=0, minute=0, second=0, microsecond=0)
        if period == "week":
            return (current - timedelta(days=current.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        return current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def _period_events(
        self,
        period: str,
        now: datetime | None = None,
    ) -> tuple[datetime, list[tuple[ErrorEvent, datetime]]]:
        current = now or datetime.now().astimezone()
        if current.tzinfo is None:
            current = current.astimezone()
        start = self._period_start(period, current)
        selected: list[tuple[ErrorEvent, datetime]] = []
        for event in self._events:
            at = event.at.astimezone(current.tzinfo)
            if start <= at <= current:
                selected.append((event, at))
        return current, selected

    def summary(
        self,
        period: str,
        now: datetime | None = None,
    ) -> PeriodSummary:
        _current, events = self._period_events(period, now)
        counts: dict[str, int] = {}
        last_seen: dict[str, datetime] = {}
        for event, at in events:
            total = counts.get(event.char, 0) + 1
            counts[event.char] = total
            previous = last_seen.get(event.char)
            if previous is None or at > previous:
                last_seen[event.char] = at

        items = tuple(
            HanziStat(char=char, count=count, last_at=last_seen[char])
            for char, count in sorted(
                counts.items(),
                key=lambda pair: (-pair[1], -last_seen[pair[0]].timestamp(), pair[0]),
            )
        )
        return PeriodSummary(period=period, total=len(events), items=items)

    def summary_by_pinyin(
        self,
        period: str,
        now: datetime | None = None,
    ) -> PinyinPeriodSummary:
        """Aggregate errors by target pinyin.

        For example, all ``shi`` mistakes are grouped together even when they
        were made on different characters such as 是 and 事.
        """
        _current, events = self._period_events(period, now)

        group_counts: dict[str, int] = {}
        group_last: dict[str, datetime] = {}
        char_counts: dict[str, dict[str, int]] = {}
        char_last: dict[str, dict[str, datetime]] = {}

        for event, at in events:
            pinyin = event.target.strip() or "—"
            group_counts[pinyin] = group_counts.get(pinyin, 0) + 1
            previous = group_last.get(pinyin)
            if previous is None or at > previous:
                group_last[pinyin] = at

            per_char = char_counts.setdefault(pinyin, {})
            per_char[event.char] = per_char.get(event.char, 0) + 1
            per_last = char_last.setdefault(pinyin, {})
            old = per_last.get(event.char)
            if old is None or at > old:
                per_last[event.char] = at

        items: list[PinyinStat] = []
        for pinyin, count in group_counts.items():
            chars = tuple(
                HanziStat(char=char, count=char_count, last_at=char_last[pinyin][char])
                for char, char_count in sorted(
                    char_counts[pinyin].items(),
                    key=lambda pair: (
                        -pair[1],
                        -char_last[pinyin][pair[0]].timestamp(),
                        pair[0],
                    ),
                )
            )
            items.append(
                PinyinStat(
                    pinyin=pinyin,
                    count=count,
                    last_at=group_last[pinyin],
                    chars=chars,
                )
            )

        items.sort(key=lambda item: (-item.count, item.pinyin))
        return PinyinPeriodSummary(
            period=period,
            total=len(events),
            items=tuple(items),
        )


class DailyInputStore:
    """Persistent per-day count of completed pinyin syllables."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._days: dict[str, int] = {}
        self._load()

    @property
    def days(self) -> dict[str, int]:
        return dict(self._days)

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return
        days = raw.get("days", {}) if isinstance(raw, dict) else {}
        if not isinstance(days, dict):
            return
        for day, count in days.items():
            try:
                value = int(count)
            except (TypeError, ValueError):
                continue
            if value > 0:
                self._days[str(day)] = value

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "days": self._days}
        temporary = self.path.with_name(self.path.name + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def add(self, count: int = 1, when: datetime | None = None) -> bool:
        if count <= 0:
            return True
        at = when or datetime.now().astimezone()
        if at.tzinfo is None:
            at = at.astimezone()
        day = at.date().isoformat()
        self._days[day] = self._days.get(day, 0) + count
        try:
            self._save()
        except OSError:
            return False
        return True

    def total_on(self, day: date) -> int:
        return self._days.get(day.isoformat(), 0)

    def today_total(self, now: datetime | None = None) -> int:
        current = now or datetime.now().astimezone()
        if current.tzinfo is None:
            current = current.astimezone()
        return self.total_on(current.date())
