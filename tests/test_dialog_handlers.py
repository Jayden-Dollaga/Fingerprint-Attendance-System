import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "python"
sys.path.insert(0, str(PYTHON_ROOT))

from gui import dialogs


def test_wipe_dialog_uses_real_confirmation_flow(monkeypatch):
    app = SimpleNamespace(
        serial_handler=SimpleNamespace(connected=True),
        wipe_status_var=None,
        wipe_confirm_button=None,
        wipe_dialog=None,
        wipe_log_text=None,
        log_message=lambda *args, **kwargs: None,
    )

    called = {}

    def fake_cmd_wipe(handler):
        called["handler"] = handler
        return True

    monkeypatch.setattr(dialogs, "cmd_wipe", fake_cmd_wipe)

    success = dialogs.confirm_wipe(app)

    assert success is True
    assert called["handler"] is app.serial_handler
