"""Chinese/English UI strings."""

from __future__ import annotations

LANGUAGES = ("zh", "en")
DEFAULT_LANGUAGE = "zh"

STRINGS: dict[str, dict[str, str]] = {
    "app_title": {
        "zh": "拼音打字练习",
        "en": "Pinyin Typing Practice",
    },
    "subtitle_loading": {
        "zh": "题库加载中…",
        "en": "Loading sentence bank…",
    },
    "subtitle_all": {
        "zh": "题库 {total} 句 · 全部句子",
        "en": "{total} sentences · All sentences",
    },
    "subtitle_group": {
        "zh": "题库 {total} 句 · {group} {count} 句",
        "en": "{total} sentences · {group} ({count})",
    },
    "subtitle_failed": {
        "zh": "题库加载失败",
        "en": "Sentence bank failed to load",
    },
    "next_sentence": {
        "zh": "换一句",
        "en": "Next sentence",
    },
    "font_size": {
        "zh": "字号",
        "en": "Font size",
    },
    "practice_group": {
        "zh": "练习分组",
        "en": "Practice group",
    },
    "show_hints": {
        "zh": "显示拼音提示",
        "en": "Show pinyin hints",
    },
    "stat_time": {"zh": "计时", "en": "Time"},
    "stat_progress": {"zh": "本句进度", "en": "Progress"},
    "stat_speed": {"zh": "速度", "en": "Speed"},
    "stat_today": {"zh": "今日输入", "en": "Today's input"},
    "input_title": {"zh": "输入拼音", "en": "Type pinyin"},
    "input_hint": {
        "zh": "无需声调 · 无需空格 · 自动分字",
        "en": "No tones · No spaces needed · Auto-grouped",
    },
    "footer_hint": {
        "zh": "Backspace 删除   ·   Enter 下一句   ·   Ctrl+R 重开   ·   F5 重载",
        "en": "Backspace Delete   ·   Enter Next   ·   Ctrl+R Restart   ·   F5 Reload",
    },
    "open_bank": {"zh": "打开题库", "en": "Open bank"},
    "reload_bank": {"zh": "重新加载题库", "en": "Reload bank"},
    "stats_button": {"zh": "错误统计", "en": "Mistake stats"},
    "status_start": {
        "zh": "输入第一个字母后开始计时。",
        "en": "Timer starts with the first letter.",
    },
    "status_restarted": {
        "zh": "已重新开始本句。",
        "en": "Sentence restarted.",
    },
    "status_enter_after_complete": {
        "zh": "整句输入完成后，按 Enter 进入下一句。",
        "en": "Finish the sentence, then press Enter.",
    },
    "status_complete": {
        "zh": "完成！用时 {seconds:.1f} 秒，按 Enter 进入下一句。",
        "en": "Done in {seconds:.1f} s. Press Enter for the next sentence.",
    },
    "status_mismatch": {
        "zh": "拼音不匹配，按 Backspace 修改。",
        "en": "Pinyin mismatch. Press Backspace to fix it.",
    },
    "status_correct": {
        "zh": "输入正确，当前字会自动前进。",
        "en": "Correct. The highlight advances automatically.",
    },
    "status_timing": {
        "zh": "计时中，继续输入即可。",
        "en": "Timer running. Keep typing.",
    },
    "status_switched": {
        "zh": "已切换到：{group}",
        "en": "Switched to: {group}",
    },
    "status_hints_on": {
        "zh": "已显示拼音提示；错字统计暂停记录。",
        "en": "Pinyin hints on. Mistake tracking is paused.",
    },
    "status_hints_off": {
        "zh": "已关闭拼音提示；之后的错字会记录到统计。",
        "en": "Pinyin hints off. New mistakes will be recorded.",
    },
    "status_bank_reloaded": {
        "zh": "题库已重新加载。",
        "en": "Sentence bank reloaded.",
    },
    "status_bank_opened": {
        "zh": "已打开题库；保存后点击“重新加载题库”。",
        "en": "Sentence bank opened. Save it, then click “Reload bank”.",
    },
    "status_group_empty": {
        "zh": "当前分组没有可用句子。",
        "en": "No sentences are available in this group.",
    },
    "status_stats_cleared": {
        "zh": "错字统计已清空。",
        "en": "Mistake statistics cleared.",
    },
    "status_language_switched": {
        "zh": "界面语言已切换。",
        "en": "Language switched.",
    },
    "status_bank_load_failed_keep": {
        "zh": "题库加载失败，仍保持当前题库。",
        "en": "Sentence bank failed to load; keeping the current bank.",
    },
    "status_bank_load_failed": {
        "zh": "无法加载 sentences.txt，请检查文件。",
        "en": "Could not load sentences.txt. Check the file.",
    },
    "status_no_sentences": {
        "zh": "题库中没有可练习的句子",
        "en": "No practice sentences available",
    },
    "dialog_bank_load_failed_title": {
        "zh": "题库加载失败",
        "en": "Sentence Bank Failed to Load",
    },
    "dialog_cannot_open_bank_title": {
        "zh": "无法打开题库",
        "en": "Could Not Open Sentence Bank",
    },
    "dialog_skipped_title": {
        "zh": "部分句子被跳过",
        "en": "Some Sentences Were Skipped",
    },
    "dialog_skipped_body": {
        "zh": "已加载 {count} 句，以下内容未载入：\n\n{detail}",
        "en": "Loaded {count} sentences. The following entries were not loaded:\n\n{detail}",
    },
    "lines_skipped_more": {
        "zh": "……另有 {count} 行",
        "en": "...and {count} more lines",
    },
    "status_loaded_skipped": {
        "zh": "已加载 {count} 句，跳过 {skipped} 行。",
        "en": "Loaded {count} sentences; skipped {skipped} lines.",
    },
    "dialog_cannot_load_bank_title": {
        "zh": "无法加载题库",
        "en": "Could Not Load Sentence Bank",
    },
    "dialog_bank_path": {
        "zh": "{message}\n\n请确认 sentences.txt 位于：\n{path}",
        "en": "{message}\n\nMake sure sentences.txt is located at:\n{path}",
    },
    "stats_title": {
        "zh": "错字统计",
        "en": "Mistake Statistics",
    },
    "stats_subtitle": {
        "zh": "只统计未显示拼音提示时的打错汉字 · 本周从周一开始",
        "en": "Only mistakes made with pinyin hints off · week starts on Monday",
    },
    "stats_view": {"zh": "查看范围", "en": "Period"},
    "stats_today": {"zh": "今天", "en": "Today"},
    "stats_week": {"zh": "本周", "en": "This week"},
    "stats_month": {"zh": "本月", "en": "This month"},
    "stats_summary": {
        "zh": "{range} · 共 {total} 次错误 · {groups} 个拼音",
        "en": "{range} · {total} errors · {groups} pinyin groups",
    },
    "stats_header_pinyin": {"zh": "拼音", "en": "Pinyin"},
    "stats_header_count": {"zh": "错误次数", "en": "Errors"},
    "stats_header_chars": {
        "zh": "汉字（按次数排序）",
        "en": "Hanzi (by count)",
    },
    "stats_header_last": {"zh": "最后出错", "en": "Last mistake"},
    "stats_empty": {
        "zh": "当前时间范围内没有打错记录",
        "en": "No mistakes in this period",
    },
    "stats_footer": {
        "zh": "只统计关闭拼音提示时的错误 · 全部显示 · 本周从周一开始",
        "en": "Only mistakes made with hints off · all entries shown · week starts on Monday",
    },
    "stats_clear": {"zh": "清空统计", "en": "Clear stats"},
    "stats_close": {"zh": "关闭", "en": "Close"},
    "stats_cleared": {
        "zh": "错字统计已清空。",
        "en": "Mistake statistics cleared.",
    },
    "period_range_week": {
        "zh": "{start} 至 {end}",
        "en": "{start} – {end}",
    },
    "period_range_month": {
        "zh": "{year} 年 {month} 月",
        "en": "{year}-{month}",
    },
    "last_time_today": {
        "zh": "最后 {time}",
        "en": "Last {time}",
    },
    "last_time_other": {
        "zh": "最后 {date} {time}",
        "en": "Last {date} {time}",
    },
    "dialog_clear_title": {"zh": "清空统计", "en": "Clear Statistics"},
    "dialog_clear_body": {
        "zh": "确定清空所有错字记录吗？此操作不可撤销。",
        "en": "Clear all mistake records? This cannot be undone.",
    },
    "unit_chars": {"zh": "字", "en": "chars"},
    "unit_cpm": {"zh": "字/分", "en": "chars/min"},
    "value_chars": {"zh": "{count} 字", "en": "{count} chars"},
    "value_cpm": {"zh": "{speed} 字/分", "en": "{speed} chars/min"},
    "value_cpm_empty": {"zh": "— 字/分", "en": "— chars/min"},
    "progress_value": {
        "zh": "{done} / {total} 字",
        "en": "{done} / {total} chars",
    },
    "theme_light": {"zh": "亮色", "en": "Light"},
    "theme_dark": {"zh": "暗色", "en": "Dark"},
    "language_switch": {"zh": "中文", "en": "EN"},
}

GROUP_LABELS: dict[str, dict[str, str]] = {
    "全部句子": {"zh": "全部句子", "en": "All sentences"},
    "未分组": {"zh": "未分组", "en": "Ungrouped"},
    "日常生活": {"zh": "日常生活", "en": "Daily life"},
    "自然四季": {"zh": "自然四季", "en": "Nature & seasons"},
    "学习与工作": {"zh": "学习与工作", "en": "Study & work"},
    "旅行与美食": {"zh": "旅行与美食", "en": "Travel & food"},
    "成语与诗词": {"zh": "成语与诗词", "en": "Idioms & poetry"},
    "绕口令与趣味": {"zh": "绕口令与趣味", "en": "Tongue twisters"},
    "生活感悟": {"zh": "生活感悟", "en": "Life reflections"},
    "更多练习": {"zh": "更多练习", "en": "More practice"},
    "小学语文课文": {"zh": "小学语文课文", "en": "Primary school texts"},
}


def tr(lang: str, key: str, **kwargs) -> str:
    entry = STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(lang) or entry.get(DEFAULT_LANGUAGE, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def group_label(lang: str, name: str) -> str:
    entry = GROUP_LABELS.get(name)
    if entry is None:
        return name
    return entry.get(lang) or entry.get(DEFAULT_LANGUAGE, name)
