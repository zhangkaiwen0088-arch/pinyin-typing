from __future__ import annotations

import unittest

from i18n import GROUP_LABELS, STRINGS, group_label, tr


class I18nTests(unittest.TestCase):
    def test_all_strings_have_both_languages(self) -> None:
        for key, translations in STRINGS.items():
            with self.subTest(key=key):
                self.assertTrue(translations.get("zh"))
                self.assertTrue(translations.get("en"))

    def test_english_formatting(self) -> None:
        self.assertEqual(tr("en", "next_sentence"), "Next sentence")
        self.assertEqual(
            tr("en", "progress_value", done=3, total=10),
            "3 / 10 chars",
        )
        self.assertEqual(
            tr("en", "status_complete", seconds=12.3),
            "Done in 12.3 s. Press Enter for the next sentence.",
        )

    def test_group_labels(self) -> None:
        self.assertEqual(group_label("en", "小学语文课文"), "Primary school texts")
        self.assertEqual(group_label("zh", "小学语文课文"), "小学语文课文")
        self.assertEqual(group_label("en", "用户自定义"), "用户自定义")
        for translations in GROUP_LABELS.values():
            self.assertTrue(translations.get("zh"))
            self.assertTrue(translations.get("en"))


if __name__ == "__main__":
    unittest.main()
