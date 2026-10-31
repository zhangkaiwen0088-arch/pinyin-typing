from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from stats import DailyInputStore, StatsStore

JST = timezone(timedelta(hours=9))
NOW = datetime(2026, 10, 30, 12, 0, tzinfo=JST)


class StatsStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.path = Path(self._temp.name) / ".stats.json"
        self.store = StatsStore(self.path)
        self._add(
            datetime(2026, 10, 30, 9, 0, tzinfo=JST),
            "天",
        )
        self._add(
            datetime(2026, 10, 30, 10, 0, tzinfo=JST),
            "天",
        )
        self._add(
            datetime(2026, 10, 30, 11, 0, tzinfo=JST),
            "气",
        )
        self._add(
            datetime(2026, 10, 29, 15, 0, tzinfo=JST),
            "天",
        )
        self._add(
            datetime(2026, 10, 26, 0, 0, tzinfo=JST),
            "人",
        )
        self._add(
            datetime(2026, 10, 25, 23, 59, tzinfo=JST),
            "地",
        )
        self._add(
            datetime(2026, 10, 5, 8, 0, tzinfo=JST),
            "人",
        )
        self._add(
            datetime(2026, 9, 30, 8, 0, tzinfo=JST),
            "地",
        )

    def tearDown(self) -> None:
        self._temp.cleanup()

    def _add(self, when: datetime, char: str) -> None:
        self.assertEqual(
            self.store.record(
                char=char,
                target="test",
                typed="te",
                sentence="测试句子。",
                when=when,
            ),
            True,
        )

    def test_today_summary(self) -> None:
        summary = self.store.summary("today", NOW)
        self.assertEqual(summary.total, 3)
        self.assertEqual(summary.items[0].char, "天")
        self.assertEqual(summary.items[0].count, 2)
        self.assertEqual(summary.items[0].last_at, datetime(2026, 10, 30, 10, 0, tzinfo=JST))
        self.assertEqual(summary.items[1].char, "气")

    def test_week_starts_on_monday(self) -> None:
        summary = self.store.summary("week", NOW)
        self.assertEqual(summary.total, 5)
        counts = {item.char: item.count for item in summary.items}
        self.assertEqual(counts["天"], 3)
        self.assertEqual(counts["人"], 1)
        self.assertNotIn("地", counts)

    def test_month_summary(self) -> None:
        summary = self.store.summary("month", NOW)
        self.assertEqual(summary.total, 7)
        counts = {item.char: item.count for item in summary.items}
        self.assertEqual(counts["天"], 3)
        self.assertEqual(counts["人"], 2)
        self.assertEqual(counts["气"], 1)
        self.assertEqual(counts["地"], 1)

    def test_pinyin_summary_groups_characters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / ".stats.json"
            store = StatsStore(path)
            when = datetime(2026, 10, 30, 9, 0, tzinfo=JST)
            for char, count, target in (
                ("是", 2, "shi"),
                ("事", 1, "shi"),
                ("天", 1, "tian"),
            ):
                for index in range(count):
                    store.record(
                        char=char,
                        target=target,
                        typed=target[:2],
                        sentence="测试。",
                        when=when + timedelta(minutes=index),
                    )
            summary = store.summary_by_pinyin("today", NOW)
        self.assertEqual(summary.total, 4)
        self.assertEqual([item.pinyin for item in summary.items], ["shi", "tian"])
        self.assertEqual(summary.items[0].count, 3)
        self.assertEqual(
            [(char.char, char.count) for char in summary.items[0].chars],
            [("是", 2), ("事", 1)],
        )

    def test_pinyin_summary_returns_all_groups(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / ".stats.json"
            store = StatsStore(path)
            for index in range(15):
                store.record(
                    char="字",
                    target=f"pin{index}",
                    typed="pin",
                    sentence="测试。",
                    when=NOW,
                )
            summary = store.summary_by_pinyin("today", NOW)
        self.assertEqual(len(summary.items), 15)

    def test_persistence(self) -> None:
        reopened = StatsStore(self.path)
        self.assertEqual(len(reopened.events), 8)
        summary = reopened.summary("today", NOW)
        self.assertEqual(summary.total, 3)
        self.assertTrue(self.path.exists())

    def test_clear_removes_events_and_file(self) -> None:
        self.store.clear()
        self.assertEqual(self.store.events, ())
        self.assertEqual(self.store.summary("today", NOW).total, 0)
        self.assertFalse(self.path.exists())

    def test_corrupt_file_is_treated_as_empty(self) -> None:
        self.path.write_text("{not valid json", encoding="utf-8")
        store = StatsStore(self.path)
        self.assertEqual(store.events, ())

    def test_invalid_period_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.store.summary("year", NOW)


class DailyInputStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.path = Path(self._temp.name) / ".daily.json"
        self.store = DailyInputStore(self.path)

    def tearDown(self) -> None:
        self._temp.cleanup()

    def test_add_and_persist_today_total(self) -> None:
        self.assertTrue(self.store.add(5, when=NOW))
        self.assertTrue(self.store.add(3, when=NOW))
        self.assertEqual(self.store.today_total(NOW), 8)
        reopened = DailyInputStore(self.path)
        self.assertEqual(reopened.today_total(NOW), 8)

    def test_totals_are_per_local_date(self) -> None:
        yesterday = NOW - timedelta(days=1)
        self.store.add(4, when=yesterday)
        self.store.add(7, when=NOW)
        self.assertEqual(self.store.today_total(NOW), 7)
        self.assertEqual(self.store.total_on(yesterday.date()), 4)

    def test_zero_or_negative_add_is_ignored(self) -> None:
        self.store.add(0, when=NOW)
        self.store.add(-3, when=NOW)
        self.assertEqual(self.store.today_total(NOW), 0)


if __name__ == "__main__":
    unittest.main()
