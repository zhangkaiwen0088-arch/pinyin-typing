from __future__ import annotations

import random
import tempfile
import unittest
from pathlib import Path

from trainer import (
    Sentence,
    SentenceBag,
    analyse,
    format_duration,
    load_sentences,
    normalize_input,
    speed_cpm,
    split_typed_chunks,
)

PROJECT_DIR = Path(__file__).resolve().parents[1]


class SentenceParsingTests(unittest.TestCase):
    def test_target_skips_punctuation(self) -> None:
        sentence = Sentence.from_text("你好，世界！")
        self.assertEqual(sentence.target, "nihaoshijie")
        self.assertEqual(sentence.han_count, 4)
        self.assertEqual([c.char for c in sentence.chars], list("你好，世界！"))
        self.assertFalse(sentence.chars[2].is_han)

    def test_phrase_context_for_polyphonic_characters(self) -> None:
        sentence = Sentence.from_text("银行音乐重庆长大山重水复绿鲤鱼")
        self.assertEqual(
            sentence.target,
            "yinhangyinyuechongqingzhangdashanchongshuifulvliyu",
        )
        self.assertEqual(
            Sentence.from_text("薄雾中若隐若现").target,
            "bowuzhongruoyinruoxian",
        )
        self.assertEqual(
            Sentence.from_text("长风破浪会有时").target,
            "changfengpolanghuiyoushi",
        )

    def test_all_shipped_sentences_parse(self) -> None:
        library = load_sentences(PROJECT_DIR / "sentences.txt")
        self.assertGreaterEqual(library.count, 100)
        self.assertEqual(len(library.skipped), 0)
        self.assertIn("小学语文课文", library.groups)
        self.assertIn("日常生活", library.groups)

    def test_group_heading_styles(self) -> None:
        content = (
            "# [日常生活]\n"
            "今天天气真好。\n"
            "# ---------- 小学语文课文 ----------\n"
            "弯弯的月儿小小的船。\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sentences.txt"
            path.write_text(content, encoding="utf-8")
            library = load_sentences(path)
        self.assertEqual(library.groups, ("日常生活", "小学语文课文"))
        self.assertEqual(library.sentences[0].group, "日常生活")
        self.assertEqual(library.sentences[1].group, "小学语文课文")

    def test_empty_sentence_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Sentence.from_text("   ")

    def test_sentence_without_han_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Sentence.from_text("hello, world!")


class NormalisationTests(unittest.TestCase):
    def test_case_spaces_and_punctuation_ignored(self) -> None:
        self.assertEqual(normalize_input("Ni Hao, Shi Jie!"), "nihaoshijie")

    def test_umlaut_can_be_typed_as_v(self) -> None:
        self.assertEqual(normalize_input("lü"), "lv")
        self.assertEqual(normalize_input("nu:"), "nv")

    def test_tone_marks_are_not_part_of_target(self) -> None:
        self.assertEqual(normalize_input("nǐ hǎo"), "nho")


class AnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sentence = Sentence.from_text("你好，世界！")

    def test_empty_input_highlights_first_character(self) -> None:
        result = analyse(self.sentence, "")
        self.assertEqual(result.completed_chars, 0)
        self.assertEqual(result.current_index, 0)
        self.assertFalse(result.is_complete)
        self.assertFalse(result.has_error)

    def test_partial_syllable_keeps_current_character(self) -> None:
        result = analyse(self.sentence, "ni")
        self.assertEqual(result.completed_chars, 1)
        self.assertEqual(result.current_index, 1)
        self.assertFalse(result.is_complete)

    def test_partial_next_syllable_also_keeps_current_character(self) -> None:
        result = analyse(self.sentence, "nih")
        self.assertEqual(result.completed_chars, 1)
        self.assertEqual(result.current_index, 1)

    def test_full_target_is_complete(self) -> None:
        result = analyse(self.sentence, "ni hao shi jie!")
        self.assertTrue(result.is_complete)
        self.assertTrue(result.is_prefix)
        self.assertIsNone(result.current_index)
        self.assertEqual(result.completed_chars, 4)
        self.assertEqual(result.progress, 1.0)

    def test_wrong_letter_is_error_and_stops_at_character(self) -> None:
        result = analyse(self.sentence, "nix")
        self.assertTrue(result.has_error)
        self.assertFalse(result.is_complete)
        self.assertEqual(result.common_prefix, 2)
        self.assertEqual(result.completed_chars, 1)
        self.assertEqual(result.current_index, 1)

    def test_extra_letters_after_target_are_not_complete(self) -> None:
        result = analyse(self.sentence, "nihaoshijiex")
        self.assertTrue(result.has_error)
        self.assertFalse(result.is_complete)
        self.assertEqual(result.completed_chars, 4)
        self.assertIsNone(result.current_index)

    def test_typed_punctuation_is_ignored(self) -> None:
        result = analyse(self.sentence, "ni，hao！shi-jie")
        self.assertEqual(result.normalized, "nihaoshijie")
        self.assertTrue(result.is_complete)


class FormattingTests(unittest.TestCase):
    def test_duration_formats_tenths(self) -> None:
        self.assertEqual(format_duration(0), "00:00.0")
        self.assertEqual(format_duration(12.34), "00:12.3")
        self.assertEqual(format_duration(65), "01:05.0")
        self.assertEqual(format_duration(-4), "00:00.0")

    def test_speed(self) -> None:
        self.assertAlmostEqual(speed_cpm(120, 60), 120.0)
        self.assertEqual(speed_cpm(12, 0), 0.0)


class TypedChunkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sentence = Sentence.from_text("你好，世界！")

    def test_empty_input_has_no_chunks(self) -> None:
        self.assertEqual(split_typed_chunks(self.sentence, ""), ())

    def test_complete_syllable_starts_next_chunk(self) -> None:
        chunks = split_typed_chunks(self.sentence, "nih")
        self.assertEqual(
            [(chunk.text, chunk.char_index) for chunk in chunks],
            [("ni", 0), ("h", 1)],
        )

    def test_punctuation_creates_no_chunk(self) -> None:
        chunks = split_typed_chunks(self.sentence, "nihaoshijie")
        self.assertEqual(
            [chunk.text for chunk in chunks],
            ["ni", "hao", "shi", "jie"],
        )

    def test_extra_input_becomes_an_error_chunk(self) -> None:
        chunks = split_typed_chunks(self.sentence, "nihaoshijiex")
        self.assertEqual(chunks[-1].text, "x")
        self.assertIsNone(chunks[-1].char_index)


class SentenceBagTests(unittest.TestCase):
    def test_every_sentence_appears_once_per_cycle(self) -> None:
        sentences = tuple(Sentence.from_text(text) for text in ("你好。", "再见。", "谢谢。"))
        bag = SentenceBag(sentences, rng=random.Random(7))
        cycle = [bag.next() for _ in range(3)]
        self.assertEqual({item.text for item in cycle}, {item.text for item in sentences})

    def test_no_immediate_repeat_between_cycles(self) -> None:
        sentences = tuple(Sentence.from_text(text) for text in ("你好。", "再见。"))
        bag = SentenceBag(sentences, rng=random.Random(3))
        previous = bag.next()
        for _ in range(50):
            current = bag.next()
            self.assertNotEqual(current, previous)
            previous = current


class LibraryLoadingTests(unittest.TestCase):
    def test_load_comments_blank_lines_and_deduplicate(self) -> None:
        content = (
            "# 注释\n"
            "\n"
            "你好，世界！\n"
            "  你好，世界！  \n"
            "今天天气真好。\n"
            "not a chinese sentence\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sentences.txt"
            path.write_text(content, encoding="utf-8")
            library = load_sentences(path)
        self.assertEqual(library.count, 2)
        self.assertEqual(len(library.skipped), 2)

    def test_utf8_bom_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sentences.txt"
            path.write_text("你好。\n", encoding="utf-8-sig")
            library = load_sentences(path)
        self.assertEqual(library.count, 1)

    def test_empty_library_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sentences.txt"
            path.write_text("# only a comment\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_sentences(path)


if __name__ == "__main__":
    unittest.main()
