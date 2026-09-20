from pathlib import Path
import subprocess


PROJECT = Path(__file__).resolve().parents[1]
MENU = PROJECT / "aval-bot-menu.sh"
INSTALLER = PROJECT / "install.sh"


def test_terminal_menu_exists_with_core_operations():
    source = MENU.read_text(encoding="utf-8")
    for marker in (
        "Start Bot",
        "Stop Bot",
        "Restart Bot",
        "Status Bot",
        "Logs Bot",
        "BOT_TOKEN",
        "ADMIN_IDS",
        "WEB_ADMIN_PASSWORD",
        "Update Bot",
        "Backup Database",
        "Remove Bot Service",
        "PURGE",
        "Exit",
    ):
        assert marker in source


def test_terminal_menu_has_no_arbitrary_command_execution():
    source = MENU.read_text(encoding="utf-8")
    assert "eval " not in source
    assert "bash -c" not in source
    assert 'systemctl "$action"' in source
    assert "read_secret" in source
    assert "chmod 600" in source


def test_terminal_menu_and_installer_are_shell_valid():
    for path in (MENU, INSTALLER):
        assert path.read_text(encoding="utf-8").startswith("#!/usr/bin/env bash")


def test_installer_installs_terminal_menu_command():
    source = INSTALLER.read_text(encoding="utf-8")
    assert "aval-bot-menu.sh" in source
    assert "/usr/local/bin/aval-bot-menu" in source
    assert "chmod 755" in source
