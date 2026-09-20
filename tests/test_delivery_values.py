import os

os.environ.setdefault("BOT_TOKEN", "123456:TEST_TOKEN")
os.environ.setdefault("ADMIN_IDS", "1")
os.environ.setdefault("REQUIRED_CHANNEL", "")

import asyncio
import bot


def _seed_order(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, "DATABASE_FILE", tmp_path / "delivery.db")
    bot.init_database()
    panel_id = bot.create_xui_panel("panel", "https://panel.example", "token", "https://sub.example/sub/{sub_id}")
    category_id = bot.create_category("category", panel_id, [1])
    product_id = bot.create_product("اشتراک", 30, 10, 67000, category_id)
    con = bot.get_db()
    con.execute(
        "INSERT INTO orders (telegram_id, product_id, amount, status, created_at, expires_at) VALUES (?,?,?,?,?,?)",
        (222, product_id, 67000, "provisioning", bot.now_text(), bot.now_text()),
    )
    con.commit()
    con.close()
    return product_id


def test_finish_xui_order_reads_duration_and_volume_from_product(tmp_path, monkeypatch):
    product_id = _seed_order(tmp_path, monkeypatch)
    result = bot._finish_xui_order(
        order_id=1,
        approved_by=0,
        email="user_1",
        links=["https://sub.example/sub/abc"],
        sub_id="abc",
        subscription_url="https://sub.example/sub/abc",
    )
    assert result["success"] is True
    assert result["product_name"] == "اشتراک"
    assert result["duration_days"] == 30
    assert result["volume_gb"] == 10.0
    assert result["price"] == 67000


def test_delivery_message_shows_real_duration_and_volume(tmp_path, monkeypatch):
    product_id = _seed_order(tmp_path, monkeypatch)
    captured = {}

    async def fake_send_photo(chat_id, photo, caption, **kwargs):
        captured["chat_id"] = chat_id
        captured["caption"] = caption

    monkeypatch.setattr(bot.bot, "send_photo", fake_send_photo)

    result = bot._finish_xui_order(
        order_id=1,
        approved_by=0,
        email="user_1",
        links=["https://sub.example/sub/abc"],
        sub_id="abc",
        subscription_url="https://sub.example/sub/abc",
    )
    asyncio.run(bot.send_product_to_user(result))

    assert captured["chat_id"] == 222
    assert "⏳ مدت: <b>30</b> روز" in captured["caption"]
    assert "📊 حجم: <b>10.0</b> GB" in captured["caption"]
    assert "💰 مبلغ: <b>67,000</b> تومان" in captured["caption"]
