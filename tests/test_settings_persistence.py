import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from settings_store import default_settings, load_settings, save_settings


def test_settings_round_trip(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings = {
        "com_port": "COM7",
        "baud_rate": 57600,
        "cooldown": 15,
        "theme": "dark",
        "auto_reconnect": False,
    }

    save_settings(settings, settings_path)
    loaded = load_settings(settings_path)

    assert loaded["com_port"] == "COM7"
    assert loaded["baud_rate"] == 57600
    assert loaded["cooldown"] == 15
    assert loaded["theme"] == "dark"
    assert loaded["auto_reconnect"] is False


def test_load_settings_merges_with_defaults(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text('{"com_port": "COM9"}', encoding="utf-8")

    loaded = load_settings(settings_path)

    assert loaded["com_port"] == "COM9"
    assert loaded["baud_rate"] == default_settings()["baud_rate"]
    assert loaded["theme"] == default_settings()["theme"]
