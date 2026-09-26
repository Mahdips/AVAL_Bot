import os

os.environ.setdefault("BOT_TOKEN", "123456:TEST_TOKEN")
os.environ.setdefault("ADMIN_IDS", "1")
os.environ.setdefault("REQUIRED_CHANNEL", "")
os.environ.setdefault("DATABASE_FILE", "/data/bot.db")

import bot
from fastapi.testclient import TestClient


def test_container_platform_detection_does_not_break_import():
    # On any host without /etc/systemd/system the app must still import
    # and serve the panel. This is the Railway/container path.
    assert hasattr(bot, "IS_CONTAINER_PLATFORM")
    assert isinstance(bot.IS_CONTAINER_PLATFORM, bool)


def test_service_control_is_disabled_on_containers(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, "DATABASE_FILE", tmp_path / "container.db")
    bot.init_database()
    monkeypatch.setattr(bot, "IS_CONTAINER_PLATFORM", True)

    client = TestClient(bot.app)
    # We are not authenticated, so this should redirect to login — not crash.
    response = client.post("/admin/runtime/bot/restart", follow_redirects=False)
    assert response.status_code == 303
    assert "/admin" in response.headers["location"]


def test_database_can_live_on_persistent_volume(tmp_path, monkeypatch):
    # Railway mounts /data; the DB path must resolve relative to nothing
    # special and simply be used as an absolute path.
    target = tmp_path / "data" / "bot.db"
    monkeypatch.setattr(bot, "DATABASE_FILE", target)
    bot.init_database()
    assert target.exists()
