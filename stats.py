"""Persistent mistyped-Hanzi statistics.

The data is deliberately stored as a small JSON file next to the project so
users can inspect or delete it.  No sentence text or keystrokes are sent
anywhere.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
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

    def summary(
        self,
        period: str,
        now: datetime | None = None,
    ) -> PeriodSummary:
        if period not in PERIODS:
            raise ValueError(f"unknown period: {period}")

        current = now or datetime.now().astimezone()
        if current.tzinfo is None:
            current = current.astimezone()

        if period == "today":
            start = current.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start = (current - timedelta(days=current.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        else:
            start = current.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )

        counts: dict[str, int] = {}
        last_seen: dict[str, datetime] = {}
        total = 0
        for event in self._events:
            at = event.at.astimezone(current.tzinfo)
            if at < start or at > current:
                continue
            total += 1
            counts[event.char] = counts.get(event.char, 0) + 1
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
        return PeriodSummary(period=period, total=total, items=items)
