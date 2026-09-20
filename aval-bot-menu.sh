#!/usr/bin/env bash
# AVAL BOT safe terminal administration menu
set -Eeuo pipefail

INSTALL_DIR="${AVAL_BOT_INSTALL_DIR:-/opt/aval-bot}"
ENV_FILE="$INSTALL_DIR/.env"
BOT_SERVICE="aval-bot"
WEB_SERVICE="aval-bot-web"

pause_menu() {
    printf '\nPress Enter to continue... '
    read -r _ || true
}

run_systemctl() {
    local action="$1" service="$2"
    case "$action:$service" in
        start:$BOT_SERVICE|stop:$BOT_SERVICE|restart:$BOT_SERVICE|status:$BOT_SERVICE|start:$WEB_SERVICE|stop:$WEB_SERVICE|restart:$WEB_SERVICE|status:$WEB_SERVICE)
            systemctl "$action" "$service"
            ;;
        *)
            echo "Invalid service operation." >&2
            return 2
            ;;
    esac
}

read_secret() {
    local label="$1" value
    read -r -s -p "$label: " value </dev/tty
    printf '\n' >&2
    printf '%s' "$value"
}

set_env_value() {
    local key="$1" value="$2" quoted
    quoted="$(printf '%s' "$value" | sed "s/'/'\\\\''/g; s/.*/'&'/")"
    if grep -qE "^${key}=" "$ENV_FILE"; then
        sed -i "s|^${key}=.*|${key}=${quoted}|" "$ENV_FILE"
    else
        printf '%s=%s\n' "$key" "$quoted" >> "$ENV_FILE"
    fi
}

change_settings() {
    [[ -f "$ENV_FILE" ]] || { echo "Config file not found: $ENV_FILE"; return 1; }
    echo "Leave a field empty to keep the current value."
    local token ids password again
    token="$(read_secret 'New BOT_TOKEN (empty = keep)')"
    ids=""
    read -r -p 'New ADMIN_IDS (empty = keep): ' ids </dev/tty
    password="$(read_secret 'New WEB_ADMIN_PASSWORD (empty = keep)')"
    if [[ -n "$password" ]]; then
        again="$(read_secret 'WEB_ADMIN_PASSWORD again')"
        [[ "$password" == "$again" ]] || { echo 'Passwords do not match.'; return 1; }
    fi
    [[ -n "$token" ]] && set_env_value BOT_TOKEN "$token"
    [[ -n "$ids" ]] && [[ "$ids" =~ ^[0-9]+(,[0-9]+)*$ ]] && set_env_value ADMIN_IDS "$ids"
    [[ -n "$ids" && ! "$ids" =~ ^[0-9]+(,[0-9]+)*$ ]] && { echo 'ADMIN_IDS format is invalid.'; return 1; }
    [[ -n "$password" ]] && set_env_value WEB_ADMIN_PASSWORD "$password"
    chmod 600 "$ENV_FILE"
    systemctl restart "$BOT_SERVICE" "$WEB_SERVICE"
    echo 'Settings saved and services restarted.'
}

update_bot() {
    echo 'Updating Bot and Web Panel from GitHub...'
    curl -fsSL https://raw.githubusercontent.com/Mahdips/AVAL_Bot/main/install.sh | bash
}

backup_database() {
    local backup_dir="$INSTALL_DIR/backups" backup_file
    mkdir -p "$backup_dir"
    backup_file="$backup_dir/bot-$(date +%Y%m%d-%H%M%S).db"
    if [[ -f "$INSTALL_DIR/bot.db" ]]; then
        cp -p "$INSTALL_DIR/bot.db" "$backup_file"
        chown avalbot:avalbot "$backup_file" 2>/dev/null || true
        chmod 600 "$backup_file"
        echo "Database backup created: $backup_file"
    else
        echo 'Database file not found.'
    fi
}

remove_bot_service() {
    echo 'This removes only the Bot service, not the Web Panel or database.'
    read -r -p 'Type REMOVE to confirm: ' confirmation </dev/tty
    [[ "$confirmation" == "REMOVE" ]] || { echo 'Cancelled.'; return 0; }
    systemctl disable --now "$BOT_SERVICE" || true
    rm -f /etc/systemd/system/aval-bot.service
    systemctl daemon-reload
    echo 'Bot service removed.'
}

purge_bot() {
    echo 'This removes the ENTIRE bot installation:'
    echo '    - aval-bot and aval-bot-web services are stopped and removed'
    echo '    - The whole install directory (/opt/aval-bot) is deleted'
    echo '    - Terminal menu, privileged helper and sudoers entry are removed'
    echo
    echo 'A copy of .env and bot.db is saved before removal at:'
    echo '    /root/aval-bot-backup-<timestamp>'
    echo
    echo 'This cannot be undone.'
    read -r -p 'Type PURGE to confirm: ' confirmation </dev/tty
    [[ "$confirmation" == "PURGE" ]] || { echo 'Cancelled.'; return 0; }

    # 1) Save a safe copy of config and database before removal
    backup_root="/root/aval-bot-backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_root"
    if [[ -f "$INSTALL_DIR/.env" ]]; then
        cp -p "$INSTALL_DIR/.env" "$backup_root/env-backup" 2>/dev/null || true
    fi
    if [[ -f "$INSTALL_DIR/bot.db" ]]; then
        cp -p "$INSTALL_DIR/bot.db" "$backup_root/bot.db" 2>/dev/null || true
    fi
    for backup_file in "$INSTALL_DIR"/backups/*.db; do
        [[ -f "$backup_file" ]] && cp -p "$backup_file" "$backup_root/" 2>/dev/null || true
    done
    chmod -R 600 "$backup_root" 2>/dev/null || true
    echo "Backup of config and database saved to: $backup_root"

    # 2) Stop and disable both services
    systemctl disable --now "$BOT_SERVICE" 2>/dev/null || true
    systemctl disable --now "$WEB_SERVICE" 2>/dev/null || true

    # 3) Remove systemd units
    rm -f "/etc/systemd/system/${BOT_SERVICE}.service"
    rm -f "/etc/systemd/system/${WEB_SERVICE}.service"
    systemctl daemon-reload

    # 4) Remove helper, sudoers and terminal menu
    rm -f /usr/local/sbin/aval-bot-admin
    rm -f /etc/sudoers.d/aval-bot-web
    rm -f /usr/local/bin/aval-bot-menu

    # 5) Remove service account and install directory
    userdel --system avalbot 2>/dev/null || true
    rm -rf "$INSTALL_DIR"

    echo
    echo 'Bot and Web Panel have been completely removed.'
    echo "Config/database backup is at: $backup_root"
    echo 'This menu will now exit.'
    exit 0
}

while true; do
    clear
    echo '========================================='
    echo '          AVAL BOT Terminal Panel'
    echo '========================================='
    echo '1) Start Bot'
    echo '2) Stop Bot'
    echo '3) Restart Bot'
    echo '4) Status Bot'
    echo '5) Logs Bot'
    echo '6) Start Web Panel'
    echo '7) Stop Web Panel'
    echo '8) Restart Web Panel'
    echo '9) Status Web Panel'
    echo '10) Change BOT_TOKEN / ADMIN_IDS / WEB_ADMIN_PASSWORD'
    echo '11) Update Bot'
    echo '12) Backup Database'
    echo '13) Remove Bot Service (keep web panel + data)'
    echo '14) PURGE: Remove everything (bot + panel + files)'
    echo '0) Exit'
    printf '\nSelect an option: '
    read -r choice </dev/tty || exit 0
    case "$choice" in
        1) run_systemctl start "$BOT_SERVICE"; pause_menu ;;
        2) run_systemctl stop "$BOT_SERVICE"; pause_menu ;;
        3) run_systemctl restart "$BOT_SERVICE"; pause_menu ;;
        4) run_systemctl status "$BOT_SERVICE" --no-pager 2>/dev/null || systemctl status "$BOT_SERVICE" --no-pager; pause_menu ;;
        5) journalctl -u "$BOT_SERVICE" -n 80 --no-pager; pause_menu ;;
        6) run_systemctl start "$WEB_SERVICE"; pause_menu ;;
        7) run_systemctl stop "$WEB_SERVICE"; pause_menu ;;
        8) run_systemctl restart "$WEB_SERVICE"; pause_menu ;;
        9) run_systemctl status "$WEB_SERVICE" --no-pager 2>/dev/null || systemctl status "$WEB_SERVICE" --no-pager; pause_menu ;;
        10) change_settings; pause_menu ;;
        11) update_bot; pause_menu ;;
        12) backup_database; pause_menu ;;
        13) remove_bot_service; pause_menu ;;
        14) purge_bot; pause_menu ;;
        0) exit 0 ;;
        *) echo 'Invalid option.'; pause_menu ;;
    esac
done