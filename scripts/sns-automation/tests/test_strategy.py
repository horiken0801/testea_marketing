from __future__ import annotations

from pathlib import Path

from socialbot.strategy import load_strategy, save_strategy


def test_load_strategy_returns_default_when_missing(tmp_path: Path) -> None:
    path = tmp_path / "strategy.json"
    strategy = load_strategy(path=path)
    assert "topics" in strategy
    assert strategy["updated_at"] is None


def test_save_strategy_sets_updated_at(tmp_path: Path) -> None:
    path = tmp_path / "strategy.json"
    strategy = load_strategy(path=path)
    save_strategy(strategy, path=path)

    reloaded = load_strategy(path=path)
    assert reloaded["updated_at"] is not None
