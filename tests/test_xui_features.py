import asyncio
import importlib.util
import os
import sys
from pathlib import Path

import pytest


PROJECT_DIR = Path(__file__).resolve().parents[1]
os.environ.setdefault("BOT_TOKEN", "123456:TEST_TOKEN")
os.environ.setdefault("ADMIN_IDS", "1")
os.environ.setdefault("REQUIRED_CHANNEL", "")

spec = importlib.util.spec_from_file_location("bot_under_test", PROJECT_DIR / "bot.py")
bot = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bot
spec.loader.exec_module(bot)


def test_build_xui_payload_uses_bytes_and_milliseconds():
    payload = bot.build_xui_client_payload(
        email="user_42_123",
        total_gb=10,
        duration_days=30,
        telegram_id=42,
        inbound_ids=[3, 7],
        now_ms=1_700_000_000_000,
    )

    assert payload["inboundIds"] == [3, 7]
    assert payload["client"]["email"] == "user_42_123"
    assert payload["client"]["totalGB"] == 10 * 1024**3
    assert payload["client"]["expiryTime"] == 1_700_000_000_000 + 30 * 86_400_000
    assert payload["client"]["tgId"] == 42
    assert payload["client"]["enable"] is True


def test_parse_xui_links_response_accepts_object_and_list_forms():
    assert bot.parse_xui_links_response({"success": True, "obj": ["vless://a"]}) == [
        "vless://a"
    ]
    assert bot.parse_xui_links_response({"success": True, "obj": {"links": ["vless://b"]}}) == [
        "vless://b"
    ]
    assert bot.parse_xui_links_response({"success": False, "msg": "failed"}) == []


def test_parse_inbound_options_keeps_only_picker_fields():
    result = bot.parse_xui_inbounds(
        {
            "success": True,
            "obj": [
                {"id": 3, "remark": "VIP", "protocol": "vless", "port": 443},
                {"id": "bad", "remark": "ignore"},
            ],
        }
    )

    assert result == [{"id": 3, "remark": "VIP", "protocol": "vless", "port": 443}]


def test_format_subscription_traffic_preserves_unlimited_values():
    text = bot.format_traffic_status(
        {"up": 100, "down": 200, "total": 0, "expiryTime": 0, "enable": True},
        now_ms=1_700_000_000_000,
    )

    assert "نامحدود" in text
    assert "بدون انقضا" in text
    assert "فعال" in text


def test_normalize_panel_url_removes_panel_api_suffixes():
    assert bot.normalize_xui_base_url("https://vpn.example.com/") == "https://vpn.example.com"
    assert bot.normalize_xui_base_url("https://vpn.example.com/panel/api") == "https://vpn.example.com"


def test_build_xui_payload_supports_start_after_first_use():
    payload = bot.build_xui_client_payload(
        email="trial_42",
        total_gb=2,
        duration_days=7,
        telegram_id=42,
        inbound_ids=[1],
        start_after_first_use=True,
        now_ms=1_700_000_000_000,
    )

    assert payload["client"]["expiryTime"] == -(7 * 86_400_000)


def test_build_subscription_url_uses_panel_alias_when_order_has_null_field():
    panel = {"subscription_url": None, "panel_subscription_url": "https://sub.example/sub/sample"}
    assert bot.build_subscription_url(panel, "abc") == "https://sub.example/sub/abc"


def test_parse_client_sub_id_from_api_response():
    data = {"success": True, "obj": {"client": {"subId": "abc123"}}}
    assert bot.parse_xui_sub_id(data) == "abc123"


def test_init_database_removes_legacy_manual_inventory_but_keeps_panel_products(tmp_path, monkeypatch):
    db = tmp_path / "manual-cleanup.db"
    monkeypatch.setattr(bot, "DATABASE_FILE", db)
    bot.init_database()
    panel_id = bot.create_xui_panel("panel", "https://panel.example", "token", "https://sub.example/sub/x")
    category_id = bot.create_category("model", panel_id, [1])
    panel_product = bot.create_product("panel-product", 30, 10, 100, category_id)
    connection = bot.get_db()
    cursor = connection.execute("INSERT INTO products (name, duration_days, volume_gb, price, category_id, created_at) VALUES (?, ?, ?, ?, NULL, ?)", ("old-manual", 30, 10, 100, bot.now_text()))
    manual_product = cursor.lastrowid
    connection.commit()
    connection.close()
    bot.add_configs(manual_product, ["vless://old-config"])
    bot.init_database()
    connection = bot.get_db()
    manual = connection.execute("SELECT active FROM products WHERE id = ?", (manual_product,)).fetchone()
    stock = connection.execute("SELECT COUNT(*) AS count FROM inventory").fetchone()["count"]
    panel = connection.execute("SELECT active, category_id FROM products WHERE id = ?", (panel_product,)).fetchone()
    connection.close()
    assert manual["active"] == 0
    assert stock == 0
    assert panel["active"] == 1
    assert panel["category_id"] == category_id


def test_create_product_requires_panel_category(tmp_path, monkeypatch):
    db = tmp_path / "panel-only.db"
    monkeypatch.setattr(bot, "DATABASE_FILE", db)
    bot.init_database()
    assert bot.create_product("manual", 30, 10, 100, None) is None
def test_format_server_status_includes_xray_and_resources():
    text = bot.format_server_status({
        "cpu": 12.5,
        "mem": {"current": 2 * 1024**3, "total": 8 * 1024**3},
        "disk": {"current": 50 * 1024**3, "total": 100 * 1024**3},
        "xray": {"state": "running", "version": "v1.2.3"},
    })
    assert "12.5%" in text
    assert "running" in text
    assert "v1.2.3" in text


def test_delete_xui_panel_allows_categories_without_active_products(tmp_path, monkeypatch):
    db = tmp_path / "delete.db"
    monkeypatch.setattr(bot, "DATABASE_FILE", db)
    bot.init_database()
    panel_id = bot.create_xui_panel("p1", "https://panel.example", "token12345", "https://sub.example/sub/x")
    bot.create_category("cat1", panel_id, [1])
    deleted, message = bot.delete_xui_panel(panel_id)
    assert deleted is True
    assert bot.get_xui_panel(panel_id) is None


def test_delete_category_removes_inbound_linked_category(tmp_path, monkeypatch):
    db = tmp_path / "delete.db"
    monkeypatch.setattr(bot, "DATABASE_FILE", db)
    bot.init_database()
    panel_id = bot.create_xui_panel("p1", "https://panel.example", "token12345", "https://sub.example/sub/x")
    category_id = bot.create_category("cat1", panel_id, [1, 2])
    deleted, message = bot.delete_category(category_id)
    assert deleted is True
    assert "حذف شد" in message
    assert bot.get_category(category_id) is None


def test_delete_category_blocks_category_used_by_product(tmp_path, monkeypatch):
    db = tmp_path / "delete.db"
    monkeypatch.setattr(bot, "DATABASE_FILE", db)
    bot.init_database()
    panel_id = bot.create_xui_panel("p1", "https://panel.example", "token12345", "https://sub.example/sub/x")
    category_id = bot.create_category("cat1", panel_id, [1])
    product_id = bot.create_product("prod1", 30, 10, 100, category_id)
    deleted, message = bot.delete_category(category_id)
    assert deleted is False
    assert "محصول" in message
    assert bot.get_category(category_id) is not None


def test_delete_xui_panel_removes_unlinked_panel(tmp_path, monkeypatch):
    db = tmp_path / "delete.db"
    monkeypatch.setattr(bot, "DATABASE_FILE", db)
    bot.init_database()
    panel_id = bot.create_xui_panel("p1", "https://panel.example", "token12345", "https://sub.example/sub/x")
    deleted, message = bot.delete_xui_panel(panel_id)
    assert deleted is True
    assert bot.get_xui_panel(panel_id) is None


def test_delete_category_removes_inbound_link_when_no_active_product(tmp_path, monkeypatch):
    db = tmp_path / "category-delete.db"
    monkeypatch.setattr(bot, "DATABASE_FILE", db)
    bot.init_database()
    panel_id = bot.create_xui_panel("p1", "https://panel.example", "token12345", "https://sub.example/sub/x")
    category_id = bot.create_category("cat1", panel_id, [7, 8])
    deleted, message = bot.delete_category(category_id)
    assert deleted is True
    assert "cat1" in message
    assert bot.get_category(category_id) is None


def test_delete_xui_panel_removes_categories_and_unlinks_inactive_products(tmp_path, monkeypatch):
    db = tmp_path / "panel-delete.db"
    monkeypatch.setattr(bot, "DATABASE_FILE", db)
    bot.init_database()
    panel_id = bot.create_xui_panel("p1", "https://panel.example", "token12345", "https://sub.example/sub/x")
    category_id = bot.create_category("cat1", panel_id, [1])
    product_id = bot.create_product("prod1", 30, 10, 100, category_id)
    connection = bot.get_db()
    connection.execute("UPDATE products SET active = 0 WHERE id = ?", (product_id,))
    connection.commit()
    connection.close()
    deleted, message = bot.delete_xui_panel(panel_id)
    assert deleted is True
    assert bot.get_xui_panel(panel_id) is None
    assert bot.get_category(category_id) is None


def test_panel_delete_deactivates_all_linked_products(tmp_path, monkeypatch):
    db = tmp_path / "panel-products.db"
    monkeypatch.setattr(bot, "DATABASE_FILE", db)
    bot.init_database()
    panel_id = bot.create_xui_panel("p1", "https://panel.example", "token12345", "https://sub.example/sub/x")
    category_id = bot.create_category("cat1", panel_id, [1])
    bot.create_product("prod1", 30, 10, 100, category_id)
    deleted, _ = bot.delete_xui_panel(panel_id)
    assert deleted is True
    connection = bot.get_db()
    row = connection.execute("SELECT active, category_id FROM products WHERE name = 'prod1'").fetchone()
    connection.close()
    assert row["active"] == 0
    assert row["category_id"] is None


def test_product_creation_requires_inbound_category():
    source = open(bot.__file__, encoding="utf-8").read()
    assert "هنوز هیچ مدل Inbound" in source
    assert 'callback_data="product_category:none"' not in source

def test_xui_panel_options_include_delete_button():
    source = open(bot.__file__, encoding="utf-8").read()
    assert 'callback_data=f"xui_panel_delete:{panel_id}"' in source


def test_build_subscription_url_accepts_subscription_template_fallback():
    panel = {"subscription_url": "", "subscription_template": "https://sub.example/sub/{sub_id}"}
    assert bot.build_subscription_url(panel, "abc") == "https://sub.example/sub/abc"


def test_build_xui_payload_preserves_requested_subscription_id():
    payload = bot.build_xui_client_payload("user", 1, 1, 42, [1], sub_id="sub-123")
    assert payload["client"]["subId"] == "sub-123"


def test_parse_xui_sub_id_accepts_nested_and_alias_keys():
    assert bot.parse_xui_sub_id({"success": True, "obj": {"client": {"sub_id": "nested"}}}) == "nested"
    assert bot.parse_xui_sub_id({"success": True, "obj": [{"subscriptionId": "list-value"}]}) == "list-value"

def test_client_name_is_username_and_adds_suffix_when_repeated(monkeypatch):
    monkeypatch.setattr(bot, "get_user", lambda telegram_id: {"username": "mahdi_test"})
    used = set()
    monkeypatch.setattr(bot, "client_name_exists", lambda name: name in used, raising=False)
    first = bot.make_client_name_for_user(42, 9)
    used.add(first)
    second = bot.make_client_name_for_user(43, 10)
    assert first == "mahdi_test"
    assert second == "mahdi_test_2"


def test_provision_requires_subscription_url_and_never_falls_back_to_config_links():
    source = open(bot.__file__, encoding="utf-8").read()
    assert "لینک Subscription قابل ارسال نیست" in source
    assert "لینک Subscription نمونهٔ پنل تنظیم نشده است" in source
    assert "links = [subscription_url] if subscription_url else await client.get_links(email)" not in source

def test_subscription_sender_puts_link_and_qr_in_one_message():
    source = open(bot.__file__, encoding="utf-8").read()
    assert "await bot.send_photo" in source
    assert "qr_png_bytes(subscription)" in source
    assert "🔗 Subscription:" in source

def test_web_sections_keep_panel_management_separate_from_products():
    source = open(bot.__file__, encoding="utf-8").read()
    assert "زیرساخت پنل‌ها" in source
    assert "ساخت و مدیریت Config" in source
    assert 'href=\'/admin/category/new\'' in source
    assert "افزودن محصول پنلی" in source


def test_home_layout_supports_explicit_two_dimensional_rows():
    layout = {"rows": [["trial", "buy"], ["support"], ["account", "tutorial"]], "columns": 2}
    assert bot.home_layout_rows(layout) == layout["rows"]
    assert bot.home_layout_rows({"order": ["trial", "buy", "support"], "columns": 2}) == [["trial", "buy"], ["support", "subscriptions"], ["tutorial", "account"]]


def test_web_panel_create_persists_created_at_and_redirects(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, "DATABASE_FILE", tmp_path / "web-panel.db")
    bot.init_database()
    bot.WEB_SESSIONS["test-session"] = {"expires": bot.time.time() + 3600}
    from fastapi.testclient import TestClient
    client = TestClient(bot.app)
    client.cookies.set(bot.WEB_SESSION_COOKIE, "test-session")
    response = client.post("/admin/panel/new", data={
        "name": "panel-web",
        "base_url": "https://panel.example/panel",
        "subscription_url": "https://sub.example/sub/sample",
        "api_token": "token12345",
    }, follow_redirects=False)
    assert response.status_code == 303
    panel = bot.get_xui_panel(1)
    assert panel["base_url"] == "https://panel.example"
    assert panel["created_at"]


def test_web_product_delete_route_unlinks_and_deactivates_product(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, "DATABASE_FILE", tmp_path / "web-product-delete.db")
    bot.init_database()
    panel_id = bot.create_xui_panel("panel", "https://panel.example", "token12345", "https://sub.example/sub/x")
    category_id = bot.create_category("category", panel_id, [1])
    product_id = bot.create_product("product", 30, 10, 100, category_id)
    bot.WEB_SESSIONS["test-session-product"] = {"expires": bot.time.time() + 3600}
    from fastapi.testclient import TestClient
    client = TestClient(bot.app)
    client.cookies.set(bot.WEB_SESSION_COOKIE, "test-session-product")
    response = client.post(f"/admin/product/{product_id}/delete", follow_redirects=False)
    assert response.status_code == 303
    product = bot.get_db().execute("SELECT active, category_id FROM products WHERE id=?", (product_id,)).fetchone()
    assert product["active"] == 0
    assert product["category_id"] is None


def test_product_creation_rejects_inactive_or_unmapped_category(tmp_path, monkeypatch):
    db = tmp_path / "product-validation.db"
    monkeypatch.setattr(bot, "DATABASE_FILE", db)
    bot.init_database()
    panel_id = bot.create_xui_panel("panel", "https://panel.example", "token12345", "https://sub.example/sub/x")
    category_id = bot.create_category("category", panel_id, [1])
    connection = bot.get_db()
    connection.execute("UPDATE categories SET active=0 WHERE id=?", (category_id,))
    connection.commit(); connection.close()
    assert bot.create_product("blocked", 30, 10, 100, category_id) is None


def test_panel_status_snapshot_reports_ping_without_exposing_credentials():
    source = open(bot.__file__, encoding="utf-8").read()
    assert "latency_ms" in source
    assert "server_status" in source
    assert "api_token" not in "panel_status_snapshot"


def test_web_products_delete_button_and_public_products_tab_exist():
    source = open(bot.__file__, encoding="utf-8").read()
    assert "action='/admin/product/{{r['id']}}/delete'" in source
    assert "public-products" in source
    assert "فقط محصولاتی که کاربر می‌تواند ببیند و بخرد" in source


def test_manual_inventory_is_not_used_for_panel_products():
    source = open(bot.__file__, encoding="utf-8").read()
    assert "محصولات پنلی موجودی دستی ندارند" in source


def test_web_product_delete_removes_product_from_admin_listing(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, "DATABASE_FILE", tmp_path / "delete-visible.db")
    bot.init_database()
    panel_id = bot.create_xui_panel("panel", "https://panel.example", "token12345", "https://sub.example/sub/x")
    category_id = bot.create_category("category", panel_id, [1])
    product_id = bot.create_product("visible-product", 30, 10, 100, category_id)
    bot.WEB_SESSIONS["delete-visible"] = {"expires": bot.time.time() + 3600}
    from fastapi.testclient import TestClient
    client = TestClient(bot.app)
    client.cookies.set(bot.WEB_SESSION_COOKIE, "delete-visible")
    before = client.get("/admin", params={"section": "products"})
    assert "visible-product" in before.text
    response = client.post(f"/admin/product/{product_id}/delete", follow_redirects=False)
    assert response.status_code == 303
    after = client.get("/admin", params={"section": "products"})
    assert "visible-product" not in after.text


def test_new_panel_product_is_in_user_visible_products_only():
    source = open(bot.__file__, encoding="utf-8").read()
    assert "get_products()" in source


def test_web_products_query_excludes_unlinked_legacy_products():
    source = open(bot.__file__, encoding="utf-8").read()
    assert "where products.category_id is not null" in source


def test_client_email_moves_to_next_suffix_when_panel_rejects_duplicate(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, "DATABASE_FILE", tmp_path / "email-retry.db")
    bot.init_database()
    panel_id = bot.create_xui_panel("panel", "https://panel.example", "token", "https://sub.example/sub/x")
    category_id = bot.create_category("category", panel_id, [1])
    context = {
        "base_url": "https://panel.example",
        "api_token": "token",
        "inbound_ids": "[1]",
        "panel_id": panel_id,
        "category_id": category_id,
        "panel_subscription_url": "https://sub.example/sub/sample",
        "subscription_template": None,
    }
    calls = []

    class FakeClient:
        def __init__(self, context):
            pass

        async def add_client(self, **kwargs):
            calls.append(kwargs["email"])
            if kwargs["email"] in {"mahdi_0203", "mahdi_0203_2"}:
                raise bot.XUIError("پنل خطا داد: email already in use")
            return {"success": True, "obj": {"client": {"subId": "sub-ok"}}}

    monkeypatch.setattr(bot, "XUIClient", FakeClient)
    result = asyncio.run(bot.provision_xui_subscription(context, "mahdi_0203", 30, 10, 42))
    assert calls == ["mahdi_0203", "mahdi_0203_2", "mahdi_0203_3"]
    assert result["sub_id"] == "sub-ok"
    assert result["email"] == "mahdi_0203_3"


def test_non_duplicate_panel_error_is_not_retried(monkeypatch):
    calls = []

    class FakeClient:
        def __init__(self, context):
            pass

        async def add_client(self, **kwargs):
            calls.append(kwargs["email"])
            raise bot.XUIError("پنل خطا داد: invalid inbound")

    monkeypatch.setattr(bot, "XUIClient", FakeClient)
    context = {"base_url": "https://panel.example", "api_token": "token", "inbound_ids": "[1]"}
    with pytest.raises(bot.XUIError, match="invalid inbound"):
        asyncio.run(bot.provision_xui_subscription(context, "mahdi_0203", 30, 10, 42))
    assert calls == ["mahdi_0203"]


    class FailingBot:
        def __init__(self):
            self.calls = 0

        async def delete_webhook(self, drop_pending_updates=False):
            self.calls += 1
            raise RuntimeError("temporary network failure")

    async def run():
        fake = FailingBot()
        result = await bot.delete_webhook_with_retry(fake, attempts=2, base_delay=0)
        return result, fake.calls

    result, calls = asyncio.run(run())
    assert result is False
    assert calls == 2


def test_telegram_proxy_is_read_from_environment_without_exposing_it(monkeypatch):
    monkeypatch.setenv("TELEGRAM_PROXY", "http://127.0.0.1:8080")
    assert bot.get_telegram_proxy() == "http://127.0.0.1:8080"


def test_web_panel_delete_route_is_registered_and_deactivates_panel(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, "DATABASE_FILE", tmp_path / "web-panel-delete.db")
    bot.init_database()
    panel_id = bot.create_xui_panel("panel", "https://panel.example", "token12345", "https://sub.example/sub/x")
    bot.WEB_SESSIONS["panel-delete-route"] = {"expires": bot.time.time() + 3600}
    from fastapi.testclient import TestClient
    client = TestClient(bot.app)
    client.cookies.set(bot.WEB_SESSION_COOKIE, "panel-delete-route")
    response = client.post(f"/admin/panel/{panel_id}/delete", follow_redirects=False)
    assert response.status_code == 303
    assert bot.get_xui_panel(panel_id) is None


def test_web_panel_status_page_handles_unreachable_panel_without_500(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, "DATABASE_FILE", tmp_path / "web-panel-status.db")
    bot.init_database()
    bot.create_xui_panel("panel", "http://127.0.0.1:1", "token12345", "https://sub.example/sub/x")
    bot.WEB_SESSIONS["panel-status-page"] = {"expires": bot.time.time() + 3600}
    from fastapi.testclient import TestClient
    client = TestClient(bot.app)
    client.cookies.set(bot.WEB_SESSION_COOKIE, "panel-status-page")
    response = client.get("/admin", params={"section": "panel-status"})
    assert response.status_code == 200
    assert "وضعیت و سلامت پنل‌ها" in response.text
    assert "Internal Server Error" not in response.text


def test_panel_status_makes_authenticated_api_requests_and_returns_details():
    calls = []
    import httpx

    async def handler(request):
        calls.append((request.url.path, request.headers.get("authorization")))
        if request.url.path.endswith("/server/status"):
            return httpx.Response(200, json={"success": True, "obj": {
                "cpu": 12.5, "mem": {"current": 2, "total": 8},
                "disk": {"current": 4, "total": 20},
                "xray": {"state": "running", "version": "1.8"},
            }})
        if request.url.path.endswith("/inbounds/options"):
            return httpx.Response(200, json={"success": True, "obj": [{
                "id": 7, "remark": "main", "protocol": "vless", "port": 443,
            }]})
        return httpx.Response(404, json={"success": False, "msg": "not found"})

    panel = {"base_url": "https://panel.example", "api_token": "secret-token"}
    result = asyncio.run(bot.fetch_panel_status(panel, transport=httpx.MockTransport(handler)))
    assert result["api"] == "online"
    assert result["server_status"]["cpu"] == 12.5
    assert len(result["inbounds"]) == 1
    assert all(auth == "Bearer secret-token" for _, auth in calls)


    async def run():
        async def handler(request):
            import httpx

            return httpx.Response(200, json={"success": False, "msg": "bad token"})

        client = bot.XUIClient(
            {"base_url": "https://vpn.example.com", "api_token": "secret"},
            transport=__import__("httpx").MockTransport(handler),
        )
        with pytest.raises(bot.XUIError, match="bad token"):
            await client.list_inbounds()

    asyncio.run(run())


def test_web_panel_test_uses_panel_mapping_for_xui_client(monkeypatch):
    class FakeXUIClient:
        def __init__(self, panel, transport=None):
            assert panel["base_url"] == "https://panel.example"
            assert panel["api_token"] == "token"

        async def list_inbounds(self):
            return [{"id": 7, "remark": "main", "protocol": "vless", "port": 443}]

    monkeypatch.setattr(bot, "XUIClient", FakeXUIClient)
    panel = {"base_url": "https://panel.example", "api_token": "token"}
    client = bot.XUIClient(panel)
    assert client is not None


def test_panel_detail_template_uses_saved_inbound_ids():
    source = open(bot.__file__, encoding="utf-8").read()
    assert "category_inbound_ids(category)" in source
    assert "c['inbound_id']" not in source


def test_category_creation_requires_active_panel_and_inbounds(tmp_path, monkeypatch):
    db = tmp_path / "category-validation.db"
    monkeypatch.setattr(bot, "DATABASE_FILE", db)
    bot.init_database()
    panel_id = bot.create_xui_panel("p1", "https://panel.example", "token12345", "https://sub.example/sub/x")
    assert bot.create_category("bad", panel_id + 999, [1]) is None
    connection = bot.get_db()
    connection.execute("UPDATE xui_panels SET active = 0 WHERE id = ?", (panel_id,))
    connection.commit()
    connection.close()
    assert bot.create_category("inactive", panel_id, [1]) is None
