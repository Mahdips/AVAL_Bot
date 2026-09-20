import os

os.environ.setdefault("BOT_TOKEN", "123456:TEST_TOKEN")
os.environ.setdefault("ADMIN_IDS", "1")
os.environ.setdefault("REQUIRED_CHANNEL", "")

import bot


def _seed(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, "DATABASE_FILE", tmp_path / "deleted.db")
    bot.init_database()
    panel_id = bot.create_xui_panel("panel", "https://panel.example", "token", "https://sub.example/sub/{sub_id}")
    category_id = bot.create_category("category", panel_id, [1])
    product_id = bot.create_product("اشتراک", 30, 10, 67000, category_id)
    created, _ = bot.create_order(222, product_id)
    order_id = created["id"]
    # شبیه‌سازی دیتابیس قدیمی: ستون‌های اسنپ‌شات روی سفارش NULL هستند
    con = bot.get_db()
    con.execute("UPDATE orders SET duration_days=NULL, volume_gb=NULL WHERE id=?", (order_id,))
    con.commit()
    con.close()
    con = bot.get_db()
    con.execute("UPDATE orders SET status='provisioning' WHERE id=?", (order_id,))
    con.commit()
    con.close()
    return product_id, order_id


def test_delivery_survives_product_soft_delete(tmp_path, monkeypatch):
    product_id, order_id = _seed(tmp_path, monkeypatch)

    # محصول بعد از خرید حذف (soft delete) می‌شود
    con = bot.get_db()
    con.execute("UPDATE products SET active=0, category_id=NULL WHERE id=?", (product_id,))
    con.commit()
    con.close()

    result = bot._finish_xui_order(
        order_id=order_id,
        approved_by=0,
        email="user_1",
        links=["https://sub.example/sub/abc"],
        sub_id="abc",
        subscription_url="https://sub.example/sub/abc",
    )
    assert result["success"] is True
    assert result["duration_days"] == 30
    assert result["volume_gb"] == 10.0
    assert result["price"] == 67000


def test_snapshot_from_order_time_is_used(tmp_path, monkeypatch):
    product_id, order_id = _seed(tmp_path, monkeypatch)

    # محصول بعد از خرید ویرایش می‌شود (مثلاً ۱۵ روز می‌شود) ولی سفارش
    # اسنپ‌شات ۳۰ روز/۱۰ گیگ خود را دارد.
    con = bot.get_db()
    con.execute("UPDATE products SET duration_days=15, volume_gb=5 WHERE id=?", (product_id,))
    con.execute("UPDATE orders SET duration_days=30, volume_gb=10 WHERE id=?", (order_id,))
    con.commit()
    con.close()

    result = bot._finish_xui_order(
        order_id=order_id,
        approved_by=0,
        email="user_1",
        links=["https://sub.example/sub/abc"],
        sub_id="abc",
        subscription_url="https://sub.example/sub/abc",
    )
    assert result["success"] is True
    # مقادیر همان لحظه خرید باید استفاده شوند، نه مقادیر جدید محصول
    assert result["duration_days"] == 30
    assert result["volume_gb"] == 10.0
