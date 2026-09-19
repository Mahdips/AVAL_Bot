import os

os.environ.setdefault("BOT_TOKEN", "123456:TEST_TOKEN")
os.environ.setdefault("ADMIN_IDS", "1")
os.environ.setdefault("REQUIRED_CHANNEL", "")

import bot


def _enable_admin_panel(monkeypatch):
    monkeypatch.setattr(bot, "web_guard", lambda request: True)


def _make_product(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, "DATABASE_FILE", tmp_path / "product-edit-flow.db")
    bot.init_database()
    panel_id = bot.create_xui_panel("panel", "https://panel.example", "token", "https://sub.example/sub/sample")
    category_id = bot.create_category("category", panel_id, [1])
    product_id = bot.create_product("old", 30, 10, 100, category_id)
    return product_id, category_id


def test_web_product_edit_page_renders_existing_values(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    _enable_admin_panel(monkeypatch)
    product_id, _ = _make_product(tmp_path, monkeypatch)
    client = TestClient(bot.app)
    response = client.get(f"/admin/product/{product_id}/edit")
    assert response.status_code == 200
    assert "ویرایش Config" in response.text
    assert "old" in response.text


def test_web_product_edit_save_updates_product_and_keeps_orders(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    _enable_admin_panel(monkeypatch)
    product_id, category_id = _make_product(tmp_path, monkeypatch)
    connection = bot.get_db()
    connection.execute(
        "INSERT INTO orders (telegram_id, product_id, amount, status, created_at, expires_at) VALUES (?,?,?,?,?,?)",
        (111, product_id, 100, "approved", bot.now_text(), bot.now_text()),
    )
    connection.commit()
    connection.close()

    client = TestClient(bot.app)
    response = client.post(
        f"/admin/product/{product_id}/edit",
        data={"name": "new", "duration_days": "60", "volume_gb": "25", "price": "250", "category_id": str(category_id)},
        follow_redirects=False,
    )
    assert response.status_code == 303

    row = bot.get_db().execute("SELECT name, duration_days, volume_gb, price FROM products WHERE id=?", (product_id,)).fetchone()
    assert dict(row) == {"name": "new", "duration_days": 60, "volume_gb": 25.0, "price": 250.0}

    order = bot.get_db().execute("SELECT status, amount FROM orders WHERE product_id=?", (product_id,)).fetchone()
    assert dict(order) == {"status": "approved", "amount": 100}


def test_web_product_edit_rejects_duplicate_name(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    _enable_admin_panel(monkeypatch)
    product_id, category_id = _make_product(tmp_path, monkeypatch)
    bot.create_product("taken", 30, 10, 100, category_id)
    client = TestClient(bot.app)
    response = client.post(
        f"/admin/product/{product_id}/edit",
        data={"name": "taken", "duration_days": "60", "volume_gb": "25", "price": "250", "category_id": str(category_id)},
    )
    assert response.status_code == 200
    assert "ویرایش انجام نشد" in response.text


def test_telegram_product_edit_handlers_are_registered():
    source = open(bot.__file__, encoding="utf-8").read()
    assert 'F.data == "product_edit_list"' in source
    assert 'F.data.startswith("product_edit:")' in source
    assert 'F.data.startswith("product_edit_category:")' in source
    assert "waiting_product_edit_name" in source
    assert "waiting_product_edit_category" in source
    assert "✏️ ویرایش Config" in source


def test_telegram_category_view_handler_is_registered():
    source = open(bot.__file__, encoding="utf-8").read()
    assert '@dp.callback_query(F.data.startswith("xui_category_view:"))' in source


def test_products_table_exposes_edit_link():
    source = open(bot.__file__, encoding="utf-8").read()
    assert "/admin/product/{{r['id']}}/edit" in source


def test_home_layout_reload_is_used_for_every_bot_response():
    source = open(bot.__file__, encoding="utf-8").read()
    assert "reply_markup=get_main_keyboard()" in source
    assert "reply_markup=main_keyboard" not in source


def test_drag_and_drop_serialization_is_safe():
    source = open(bot.__file__, encoding="utf-8").read()
    assert "dataTransfer.setData" in source
    assert '.layout-btn' in source
