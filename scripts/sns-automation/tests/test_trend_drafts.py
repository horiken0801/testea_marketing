from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from socialbot.trend_drafts import (
    DraftParseError,
    DraftPost,
    PLATFORM_MAX_CHARS,
    build_prompt,
    extract_json,
    load_reference_notes,
    render_markdown,
)

JST = ZoneInfo("Asia/Tokyo")


def test_extract_json_parses_result_block() -> None:
    text = 'ここまでが調査です。\n<result>\n[{"topic": "a"}]\n</result>\n'
    assert extract_json(text) == [{"topic": "a"}]


def test_extract_json_raises_when_missing_tag() -> None:
    with pytest.raises(DraftParseError):
        extract_json("resultタグなしのテキスト")


def test_extract_json_raises_on_invalid_json() -> None:
    with pytest.raises(DraftParseError):
        extract_json("<result>not json</result>")


def test_load_reference_notes_skips_readme_and_non_text_files(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("読み込まれない", encoding="utf-8")
    (tmp_path / "notes.md").write_text("過去投稿メモ", encoding="utf-8")
    (tmp_path / "ignore.json").write_text('{"a": 1}', encoding="utf-8")

    notes = load_reference_notes([tmp_path])

    assert "過去投稿メモ" in notes
    assert "読み込まれない" not in notes
    assert "ignore.json" not in notes


def test_load_reference_notes_returns_empty_when_dir_missing(tmp_path: Path) -> None:
    assert load_reference_notes([tmp_path / "does-not-exist"]) == ""


def test_load_reference_notes_merges_multiple_dirs(tmp_path: Path) -> None:
    shared = tmp_path / "shared"
    x_only = tmp_path / "x_only"
    shared.mkdir()
    x_only.mkdir()
    (shared / "threads_notes.md").write_text("Threadsの過去実績", encoding="utf-8")
    (x_only / "x_notes.md").write_text("Xの運用ルール", encoding="utf-8")

    notes = load_reference_notes([shared, x_only])

    assert "Threadsの過去実績" in notes
    assert "Xの運用ルール" in notes


@pytest.mark.parametrize("platform", ["threads", "x"])
def test_render_markdown_includes_draft_fields(platform: str) -> None:
    draft = DraftPost(
        topic="模試シーズン",
        insight="秋の模試が本格化する時期",
        post_text="本文サンプル",
        suggested_datetime="2026-08-20T12:30:00+09:00",
        reasoning="平日昼が反応良い傾向",
        sources=["https://example.com"],
    )

    markdown = render_markdown(platform, [draft], datetime(2026, 8, 14, 9, 0, tzinfo=JST))

    assert "模試シーズン" in markdown
    assert "本文サンプル" in markdown
    assert "https://example.com" in markdown
    assert "2026-08-20T12:30:00+09:00" in markdown


def test_render_markdown_shows_optional_x_metadata_when_present() -> None:
    draft = DraftPost(
        topic="HP誘導",
        insight="書籍・記事の一覧ページに興味を持たれやすい",
        post_text="本文サンプル",
        suggested_datetime="2026-08-18T12:30:00+09:00",
        reasoning="火12:30は過去実績で最強のHP誘導枠",
        sources=[],
        category="HP誘導",
        expected_engagement="imp 40-50",
        destination_url="https://testea.net/books/",
    )

    markdown = render_markdown("x", [draft], datetime(2026, 8, 14, 9, 0, tzinfo=JST))

    assert "カテゴリ: HP誘導" in markdown
    assert "想定反応目安: imp 40-50" in markdown
    assert "誘導先URL: https://testea.net/books/" in markdown


def test_render_markdown_omits_optional_metadata_when_absent() -> None:
    draft = DraftPost(
        topic="夏設計",
        insight="お盆明けの立て直し",
        post_text="本文サンプル",
        suggested_datetime="2026-08-15T20:00:00+09:00",
        reasoning="休日夜の生活導線",
        sources=[],
    )

    markdown = render_markdown("threads", [draft], datetime(2026, 8, 14, 9, 0, tzinfo=JST))

    assert "カテゴリ:" not in markdown
    assert "想定反応目安:" not in markdown
    assert "誘導先URL:" not in markdown


def test_build_prompt_uses_platform_specific_char_limit() -> None:
    juken_config = {
        "topic_area": "中学受験",
        "audience": "保護者",
        "tone": "テストトーン",
        "hashtags": [],
        "posts_per_run": 2,
    }
    today = datetime(2026, 8, 14, 9, 0, tzinfo=JST)

    x_prompt = build_prompt("x", juken_config, "", today)
    threads_prompt = build_prompt("threads", juken_config, "", today)

    assert f"{PLATFORM_MAX_CHARS['x']}文字以内" in x_prompt
    assert f"{PLATFORM_MAX_CHARS['threads']}文字以内" in threads_prompt
    assert "X（旧Twitter）" in x_prompt
    assert "Threads" in threads_prompt


def test_build_prompt_notes_cross_platform_reference_data() -> None:
    juken_config = {"topic_area": "中学受験", "audience": "保護者", "tone": "", "posts_per_run": 1}
    today = datetime(2026, 8, 14, 9, 0, tzinfo=JST)

    prompt = build_prompt("x", juken_config, "過去のThreads投稿メモ", today)

    assert "他プラットフォーム" in prompt
    assert "過去のThreads投稿メモ" in prompt


def test_research_and_draft_drops_destination_url_not_in_allowlist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import socialbot.trend_drafts as trend_drafts
    from socialbot.config import Config

    reference_dir = tmp_path / "reference"
    reference_dir.mkdir()
    (reference_dir / "urls.md").write_text(
        "許可URL一覧: https://testea.net/about/", encoding="utf-8"
    )

    juken_config_path = tmp_path / "config.json"
    juken_config_path.write_text(
        '{"topic_area": "中学受験", "audience": "保護者", "tone": "", "posts_per_run": 1}',
        encoding="utf-8",
    )

    fake_response = """<result>
[
  {"topic": "a", "insight": "i", "post_text": "text", "suggested_datetime": "2026-08-18T12:30:00+09:00", "reasoning": "r", "sources": [], "destination_url": "https://evil.example.com/"},
  {"topic": "b", "insight": "i", "post_text": "text", "suggested_datetime": "2026-08-19T12:30:00+09:00", "reasoning": "r", "sources": [], "destination_url": "https://testea.net/about/"}
]
</result>"""
    monkeypatch.setattr(trend_drafts, "call_claude_research", lambda config, prompt: fake_response)

    config = Config(anthropic_api_key="dummy-key")
    drafts, _raw = trend_drafts.research_and_draft(config, "x", juken_config_path, [reference_dir])

    assert drafts[0].destination_url == ""  # 一覧に無いURLは除去される
    assert drafts[1].destination_url == "https://testea.net/about/"  # 一覧にあるURLは残る
