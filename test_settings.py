import json
import os

import pytest

from upt.settings import Settings


def test_session_roundtrip_paths_only(tmp_path):
    settings = Settings(tmp_path / "config" / "session.json")
    assert settings.load() == {}
    settings.save(tmp_path / "notes", tmp_path / "notes" / "résumé.md")
    assert settings.load() == {"workspace": str(tmp_path / "notes"),
                               "document": str(tmp_path / "notes" / "résumé.md")}
    settings.save(None, None)
    assert settings.load() == {"workspace": "", "document": ""}


@pytest.mark.parametrize("content", ['{"broken"', "[]", '"str"', "X" * 17000],
                         ids=["invalid-json", "list", "string", "oversize"])
def test_corrupt_settings_visible(tmp_path, content):
    path = tmp_path / "session.json"
    path.write_text(content)
    with pytest.raises(ValueError, match="restore"):
        Settings(path).load()


def test_unknown_and_invalid_fields_ignored(tmp_path):
    path = tmp_path / "session.json"
    path.write_text(json.dumps({"workspace": 42, "document": "safe", "telemetry": True}))
    assert Settings(path).load() == {"document": "safe"}


def test_settings_failed_commit_keeps_previous_session(tmp_path, monkeypatch):
    settings = Settings(tmp_path / "session.json")
    settings.save(tmp_path, None)
    previous = settings.path.read_bytes()

    def denied(*args):
        raise PermissionError("injected failure")

    monkeypatch.setattr(os, "replace", denied)
    with pytest.raises(PermissionError):
        settings.save(None, None)
    assert settings.path.read_bytes() == previous
    assert list(tmp_path.iterdir()) == [settings.path]
