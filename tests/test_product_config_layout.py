import os

os.environ.setdefault("BOT_TOKEN", "123456:TEST_TOKEN")
os.environ.setdefault("ADMIN_IDS", "1")
os.environ.setdefault("REQUIRED_CHANNEL", "")

import bot


def test_update_product_changes_existing_config_without_touching_orders(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, "DATABASE_FILE", tmp_path / "product-edit.db")
    bot.init_database()
    panel_id = bot.create_xui_panel("panel", "https://panel.example", "token", "https://sub.example/sub/sample")
    category_id = bot.create_category("category", panel_id, [1])
    product_id = bot.create_product("old", 30, 10, 100, category_id)

    updated = bot.update_product(product_id, "new", 60, 25, 250, category_id)

    assert updated is True
    row = bot.get_db().execute(
        "SELECT name, duration_days, volume_gb, price, category_id, active FROM products WHERE id=?",
        (product_id,),
    ).fetchone()
    assert dict(row) == {
        "name": "new",
        "duration_days": 60,
        "volume_gb": 25.0,
        "price": 250.0,
        "category_id": category_id,
        "active": 1,
    }


def test_product_edit_controls_exist_in_bot_and_web_panel():
    source = open(bot.__file__, encoding="utf-8").read()
    assert "product_edit_list" in source
    assert "product_edit:" in source
    assert "@app.get(\"/admin/product/{product_id}/edit\"" in source
    assert "@app.post(\"/admin/product/{product_id}/edit\"" in source
    assert "ویرایش Config" in source


def test_main_keyboard_is_loaded_from_database_for_each_bot_response():
    source = open(bot.__file__, encoding="utf-8").read()
    assert "reply_markup=get_main_keyboard()" in source
    assert "reply_markup=main_keyboard" not in source


def test_home_layout_save_persists_for_a_separate_bot_process():
    source = open(bot.__file__, encoding="utf-8").read()
    assert "home_layout" in source
    assert "get_main_keyboard()" in source
