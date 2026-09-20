import os

os.environ.setdefault("BOT_TOKEN", "123456:TEST_TOKEN")
os.environ.setdefault("ADMIN_IDS", "1")
os.environ.setdefault("REQUIRED_CHANNEL", "")
os.environ.setdefault("BACKUP_INTERVAL_HOURS", "6")

import asyncio

import bot


def test_backup_interval_defaults_to_six_hours():
    import importlib

    importlib.reload(bot)
    assert bot.BACKUP_INTERVAL_HOURS == 6


def test_prune_keeps_only_latest(tmp_path):
    # ساخت ۱۰ بک‌آپ ساختگی و بررسی اینکه فقط N تا نگه داشته می‌شوند
    created = []
    for i in range(10):
        path = tmp_path / f"bot_backup_2026010{i}_000000.db"
        path.write_bytes(b"x")
        import time

        t = time.time() + i
        os.utime(path, (t, t))
        created.append(path)

    removed = bot.prune_database_backups(tmp_path, keep=3)
    assert removed == 7
    remaining = sorted(tmp_path.glob("bot_backup_*.db"))
    assert len(remaining) == 3
    assert remaining[-1].name == created[-1].name


def test_backup_worker_sends_document_to_admins(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, "DATABASE_FILE", tmp_path / "worker.db")
    bot.init_database()

    captured = {}

    async def fake_send_document(chat_id, document, caption=None, **kwargs):
        captured["chat_id"] = chat_id
        captured["caption"] = caption

    monkeypatch.setattr(bot.bot, "send_document", fake_send_document)
    monkeypatch.setattr(bot, "BACKUP_INTERVAL_HOURS", 0)  # برای تست: بدون انتظار

    async def run_one_cycle():
        task = asyncio.create_task(bot.backup_worker())
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(run_one_cycle())
    assert captured["chat_id"] == 1
    assert "بک‌آپ" in captured["caption"]
    assert "هر 0 ساعت" in captured["caption"]
