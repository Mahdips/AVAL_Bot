import pytest

from admin_control import (
    build_service_command,
    update_env_file,
    update_env_text,
    validate_config_updates,
)


def test_update_env_text_preserves_unrelated_values_and_quotes_values(tmp_path):
    original = "BOT_TOKEN='old'\nADMIN_IDS='1,2'\nWEB_PORT='8090'\n"
    target = tmp_path / ".env"
    target.write_text(original, encoding="utf-8")

    update_env_file(target, {"BOT_TOKEN": "12345:abcdefghijklmnopqrstuvwxyz123456", "ADMIN_IDS": "7,8"})

    result = target.read_text(encoding="utf-8")
    assert "BOT_TOKEN='12345:abcdefghijklmnopqrstuvwxyz123456'" in result
    assert "ADMIN_IDS='7,8'" in result
    assert "WEB_PORT='8090'" in result
    assert "old" not in result
    assert not (tmp_path / ".env.tmp").exists()


def test_validate_config_updates_rejects_unknown_keys_and_invalid_ids():
    with pytest.raises(ValueError):
        validate_config_updates({"NOT_ALLOWED": "x"})

    with pytest.raises(ValueError):
        validate_config_updates({"ADMIN_IDS": "12, bad"})


def test_validate_config_updates_accepts_password_without_returning_it():
    updates = validate_config_updates(
        {
            "BOT_TOKEN": "123456:abcdefghijklmnopqrstuvwxyz123456",
            "ADMIN_IDS": "123,456",
            "WEB_ADMIN_PASSWORD": "a strong password",
        }
    )

    assert updates["ADMIN_IDS"] == "123,456"
    assert updates["WEB_ADMIN_PASSWORD"] == "a strong password"


def test_build_service_command_allows_only_safe_known_actions():
    assert build_service_command("bot", "restart") == ["sudo", "-n", "/usr/local/sbin/aval-bot-admin", "bot", "restart"]
    assert build_service_command("bot", "remove") == ["sudo", "-n", "/usr/local/sbin/aval-bot-admin", "bot", "remove"]
    assert build_service_command("web", "status") == ["sudo", "-n", "/usr/local/sbin/aval-bot-admin", "web", "status"]

    with pytest.raises(ValueError):
        build_service_command("database", "restart")

    with pytest.raises(ValueError):
        build_service_command("web", "delete")


def test_runtime_settings_allow_omitting_password_update():
    updates = validate_config_updates({"ADMIN_IDS": "123"})
    assert updates == {"ADMIN_IDS": "123"}


def test_runtime_page_never_contains_partial_bot_token():
    source = open("bot.py", encoding="utf-8").read()
    assert "[:5]" not in source
    assert "تنظیم شده (مخفی)" in source
