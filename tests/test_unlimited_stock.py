import os

os.environ.setdefault("BOT_TOKEN", "123456:TEST_TOKEN")
os.environ.setdefault("ADMIN_IDS", "1")
os.environ.setdefault("REQUIRED_CHANNEL", "")

import asyncio
import types

import bot


def test_products_keyboard_never_shows_stock(tmp_path, monkeypatch):
    """موجودی محصول به کاربر نمایش داده نمی‌شود (نه عدد، نه «نامحدود»)."""
    monkeypatch.setattr(bot, "DATABASE_FILE", tmp_path / "stock.db")
    bot.init_database()
    panel_id = bot.create_xui_panel("panel", "https://panel.example", "token", "https://sub.example/sub/{sub_id}")
    category_id = bot.create_category("category", panel_id, [1])
    bot.create_product("اشتراک", 30, 10, 67000, category_id)

    keyboard = bot.products_keyboard()
    labels = [btn.text for row in keyboard.inline_keyboard for btn in row]
    assert any("اشتراک" in label for label in labels), labels
    assert not any("موجودی" in label for label in labels), labels
    assert not any("نامحدود" in label for label in labels), labels


def test_admin_report_never_shows_stock(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, "DATABASE_FILE", tmp_path / "report.db")
    bot.init_database()
    panel_id = bot.create_xui_panel("panel", "https://panel.example", "token", "https://sub.example/sub/{sub_id}")
    category_id = bot.create_category("category", panel_id, [1])
    bot.create_product("اشتراک", 30, 10, 67000, category_id)

    captured = {}

    async def fake_answer(text, **kwargs):
        captured["text"] = text

    message = types.SimpleNamespace(
        answer=fake_answer,
        from_user=types.SimpleNamespace(id=1),
    )

    asyncio.run(bot.products_report(message))
    assert "اشتراک" in captured["text"]
    # بخش موجودی محصول نباید وجود داشته باشد (خط «📦 موجودی»)
    assert "📦 موجودی" not in captured["text"]
    assert "نامحدود" not in captured["text"]
