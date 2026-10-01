import os

os.environ.setdefault("BOT_TOKEN", "123456:TEST_TOKEN")
os.environ.setdefault("ADMIN_IDS", "1")
os.environ.setdefault("REQUIRED_CHANNEL", "")

import bot


def test_detect_panel_address_prefers_railway_domain(monkeypatch):
    monkeypatch.setenv("RAILWAY_PUBLIC_DOMAIN", "aval-bot-railway.up.railway.app")
    monkeypatch.setenv("WEB_PUBLIC_IP", "1.2.3.4")
    assert bot.detect_panel_address() == "https://aval-bot-railway.up.railway.app/admin"


def test_detect_panel_address_falls_back_to_ip(monkeypatch):
    monkeypatch.delenv("RAILWAY_PUBLIC_DOMAIN", raising=False)
    monkeypatch.setenv("WEB_PUBLIC_IP", "1.2.3.4")
    monkeypatch.setenv("WEB_PORT", "8090")
    assert bot.detect_panel_address() == "http://1.2.3.4:8090/admin"
