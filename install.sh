#!/usr/bin/env bash
# AVAL BOT one-command Linux installer
set -Eeuo pipefail

INSTALL_DIR="${AVAL_BOT_INSTALL_DIR:-/opt/aval-bot}"
SERVICE_NAME="aval-bot"
WEB_SERVICE_NAME="aval-bot-web"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
WEB_SERVICE_FILE="/etc/systemd/system/${WEB_SERVICE_NAME}.service"
SCRIPT_PATH="${BASH_SOURCE[0]:-}"
SOURCE_DIR=""
if [[ -n "$SCRIPT_PATH" && -f "$SCRIPT_PATH" ]]; then
    SOURCE_DIR="$(cd -- "$(dirname -- "$SCRIPT_PATH")" && pwd)"
fi
DRY_RUN=0
REPO_URL="${AVAL_BOT_REPO:-https://github.com/Mahdips/AVAL_Bot}"

installer_error() {
    echo "Installer failed at line ${BASH_LINENO[0]:-unknown}." >&2
}
trap installer_error ERR
REPO_REF="${AVAL_BOT_REF:-main}"
REMOTE_TMP=""
NO_START=0

usage() {
    cat <<'EOF'
AVAL BOT installer

Run from the project folder:
  sudo bash install.sh

Options:
  --repo URL     install directly from a public GitHub repository
  --ref REF      GitHub branch/tag/commit (default: main)
  --update       update code/dependencies and restart the service
  --no-start     install only; do not start the service
  --dry-run      validate the installer without changing the system
  -h, --help     show this help

Environment:
  AVAL_BOT_INSTALL_DIR=/opt/aval-bot
  AVAL_BOT_REPO=https://github.com/Mahdips/AVAL_Bot
  AVAL_BOT_REF=main
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo)
            [[ $# -ge 2 ]] || { echo "--repo requires a URL" >&2; exit 2; }
            REPO_URL="$2"; shift 2 ;;
        --ref)
            [[ $# -ge 2 ]] || { echo "--ref requires a branch/tag" >&2; exit 2; }
            REPO_REF="$2"; shift 2 ;;
        --dry-run) DRY_RUN=1; shift ;;
        --update) shift ;;
        --no-start) NO_START=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

# Download source only when the script was piped from curl or the local source is missing.
if [[ -z "$SOURCE_DIR" || ! -f "$SOURCE_DIR/bot.py" ]]; then
    command -v curl >/dev/null 2>&1 || { echo "curl is required for GitHub installation." >&2; exit 1; }
    command -v tar >/dev/null 2>&1 || { echo "tar is required for GitHub installation." >&2; exit 1; }
    REMOTE_TMP="$(mktemp -d)"
    trap 'rm -rf "$REMOTE_TMP"' EXIT
    echo "Downloading AVAL BOT from GitHub..."
    REPO_PATH="${REPO_URL#https://github.com/}"
    REPO_PATH="${REPO_PATH#http://github.com/}"
    REPO_PATH="${REPO_PATH%.git}"
    ARCHIVE_URL="https://codeload.github.com/${REPO_PATH}/tar.gz/${REPO_REF}"
    curl -fsSL --retry 3 "$ARCHIVE_URL" -o "$REMOTE_TMP/source.tar.gz"
    mkdir -p "$REMOTE_TMP/src"
    tar -xzf "$REMOTE_TMP/source.tar.gz" -C "$REMOTE_TMP/src"
    SOURCE_DIR="$(find "$REMOTE_TMP/src" -mindepth 1 -maxdepth 1 -type d -print -quit)"
fi

if [[ "$DRY_RUN" == "1" ]]; then
    if [[ -n "$REPO_URL" ]]; then
        echo "Dry run OK: GitHub $REPO_URL@$REPO_REF -> $INSTALL_DIR"
    else
        [[ -n "$SOURCE_DIR" ]] || { echo "Run from a project folder or pass --repo URL." >&2; exit 1; }
        [[ -f "$SOURCE_DIR/bot.py" ]] || { echo "bot.py not found in $SOURCE_DIR" >&2; exit 1; }
        [[ -f "$SOURCE_DIR/requirements.txt" ]] || { echo "requirements.txt not found in $SOURCE_DIR" >&2; exit 1; }
        echo "Dry run OK: $SOURCE_DIR -> $INSTALL_DIR"
    fi
    exit 0
fi

if [[ "$(id -u)" -ne 0 ]]; then
    echo "Run this installer with sudo: sudo bash install.sh" >&2
    exit 1
fi

command -v apt-get >/dev/null 2>&1 || { echo "This installer supports Debian/Ubuntu Linux (apt-get)." >&2; exit 1; }
[[ -n "$SOURCE_DIR" ]] || { echo "Run from a project folder or pass --repo URL." >&2; exit 1; }
[[ -f "$SOURCE_DIR/bot.py" ]] || { echo "bot.py not found in $SOURCE_DIR" >&2; exit 1; }
[[ -f "$SOURCE_DIR/requirements.txt" ]] || { echo "requirements.txt not found in $SOURCE_DIR" >&2; exit 1; }

# Disable stale optional Ookla source before apt-get update.
disable_broken_optional_apt_sources() {
    local source
    shopt -s nullglob
    for source in /etc/apt/sources.list.d/*; do
        if [[ -f "$source" ]] && grep -q 'packagecloud.io/ookla/speedtest-cli' "$source" 2>/dev/null; then
            mv "$source" "$source.avalbot-disabled"
            echo "Disabled stale optional APT source: $(basename "$source")"
        fi
    done
    shopt -u nullglob
}
disable_broken_optional_apt_sources

export DEBIAN_FRONTEND=noninteractive
echo "[1/7] Installing system dependencies..."
apt-get update -y
apt-get install -y python3 python3-venv python3-pip ca-certificates curl tar

mkdir -p "$INSTALL_DIR"

# Copy application files, while never overwriting an existing database or .env.
echo "[2/7] Copying application files to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR/tests"
for item in bot.py admin_control.py aval-bot-menu.sh requirements.txt .env.example README.md tests/test_admin_control.py tests/test_terminal_menu.py tests/test_product_edit.py tests/test_product_config_layout.py; do
    if [[ -f "$SOURCE_DIR/$item" ]]; then
        cp -f "$SOURCE_DIR/$item" "$INSTALL_DIR/$item"
    fi
done
if [[ ! -f "$INSTALL_DIR/.env" && -f "$SOURCE_DIR/.env" ]]; then
    cp -f "$SOURCE_DIR/.env" "$INSTALL_DIR/.env"
fi
if [[ ! -f "$INSTALL_DIR/bot.db" && -f "$SOURCE_DIR/bot.db" ]]; then
    cp -f "$SOURCE_DIR/bot.db" "$INSTALL_DIR/bot.db"
fi
cp -f "$SOURCE_DIR/install.sh" "$INSTALL_DIR/install.sh"
chmod 750 "$INSTALL_DIR/install.sh"
if [[ -f "$INSTALL_DIR/aval-bot-menu.sh" ]]; then
    install -m 755 "$INSTALL_DIR/aval-bot-menu.sh" /usr/local/bin/aval-bot-menu
fi

VENV_DIR="$INSTALL_DIR/.venv"
echo "[3/7] Preparing Python environment and dependencies..."
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
echo "[3/7] Python dependencies ready. Configuring environment..."

ENV_FILE="$INSTALL_DIR/.env"
touch "$ENV_FILE"
chmod 600 "$ENV_FILE"

# Read existing values only to avoid asking again during an update.
set -a
# shellcheck disable=SC1090
source "$ENV_FILE" || true
set +a

if [[ ! -t 0 && ! -r /dev/tty ]]; then
    echo "Interactive terminal is required for first installation." >&2
    echo "Run the command directly in SSH, not from a background job." >&2
    exit 1
fi

prompt_secret() {
    # Legacy hidden prompt, kept for reuse; installation uses prompt_secret_show
    # below so the user can see what they type during first setup.
    local label="$1"
    local current="${2:-}"
    local value
    if [[ -n "$current" ]]; then
        read -r -s -p "$label (Enter = keep existing): " value </dev/tty
    else
        read -r -s -p "$label: " value </dev/tty
    fi
    printf '\n' >&2
    if [[ -n "$value" ]]; then
        printf '%s' "$value"
    else
        printf '%s' "$current"
    fi
}

prompt_password() {
    local label="$1"
    local current="${2:-}"
    local value confirmation
    while true; do
        if [[ -n "$current" ]]; then
            read -r -p "$label (Enter = keep existing): " value </dev/tty
            if [[ -z "$value" ]]; then
                printf '\n' >&2
                printf '%s' "$current"
                return
            fi
        else
            read -r -p "$label: " value </dev/tty
        fi
        printf '\n' >&2
        read -r -p "$label again: " confirmation </dev/tty
        printf '\n' >&2
        if [[ "$value" == "$confirmation" && -n "$value" ]]; then
            printf '%s' "$value"
            return
        fi
        echo "Passwords do not match; please try again." >&2
    done
}

prompt_secret_show() {
    # Same as prompt_secret but shows what the user types during first setup.
    local label="$1"
    local current="${2:-}"
    local value
    if [[ -n "$current" ]]; then
        read -r -p "$label (Enter = keep existing): " value </dev/tty
    else
        read -r -p "$label: " value </dev/tty
    fi
    printf '\n' >&2
    if [[ -n "$value" ]]; then
        printf '%s' "$value"
    else
        printf '%s' "$current"
    fi
}

prompt_value() {
    local label="$1"
    local current="${2:-}"
    local value
    if [[ -n "$current" ]]; then
        read -r -p "$label (Enter = keep existing): " value </dev/tty
    else
        read -r -p "$label: " value </dev/tty
    fi
    if [[ -n "$value" ]]; then
        printf '%s' "$value"
    else
        printf '%s' "$current"
    fi
}

# Use single-quoted dotenv values and escape backslashes/apostrophes.
dotenv_quote() {
    local value="$1"
    value="${value//\\/\\\\}"
    value="${value//\'/\'\\\'\'}"
    printf "'%s'" "$value"
}

set_env_value() {
    local key="$1"
    local value="$2"
    local quoted
    quoted="$(dotenv_quote "$value")"
    if grep -qE "^${key}=" "$ENV_FILE"; then
        sed -i "s|^${key}=.*|${key}=${quoted}|" "$ENV_FILE"
    else
        printf '%s=%s\n' "$key" "$quoted" >> "$ENV_FILE"
    fi
}

validate_bot_token() {
    printf '%s' "$1" | "$VENV_DIR/bin/python" -c 'import sys; from aiogram.utils.token import validate_token; validate_token(sys.stdin.read())' >/dev/null 2>&1
}

validate_admin_ids() {
    [[ "$1" =~ ^[0-9]+(,[0-9]+)*$ ]]
}

if [[ -z "${BOT_TOKEN:-}" ]]; then
    BOT_TOKEN="$(prompt_secret_show 'BOT_TOKEN (from BotFather)')"
    [[ -n "$BOT_TOKEN" ]] || { echo "BOT_TOKEN is required." >&2; exit 1; }
    set_env_value BOT_TOKEN "$BOT_TOKEN"
else
    BOT_TOKEN="$(prompt_secret_show 'BOT_TOKEN (from BotFather)' "$BOT_TOKEN")"
    [[ -n "$BOT_TOKEN" ]] || { echo "BOT_TOKEN is required." >&2; exit 1; }
    set_env_value BOT_TOKEN "$BOT_TOKEN"
fi
if [[ -z "${ADMIN_IDS:-}" ]]; then
    ADMIN_IDS="$(prompt_value 'ADMIN_IDS (numeric Telegram IDs, comma-separated)')"
    [[ -n "$ADMIN_IDS" ]] || { echo "ADMIN_IDS is required." >&2; exit 1; }
    set_env_value ADMIN_IDS "$ADMIN_IDS"
else
    ADMIN_IDS="$(prompt_value 'ADMIN_IDS (numeric Telegram IDs, comma-separated)' "$ADMIN_IDS")"
    [[ -n "$ADMIN_IDS" ]] || { echo "ADMIN_IDS is required." >&2; exit 1; }
    set_env_value ADMIN_IDS "$ADMIN_IDS"
fi
if [[ -z "${WEB_ADMIN_PASSWORD:-}" ]]; then
    WEB_ADMIN_PASSWORD="$(prompt_password 'WEB_ADMIN_PASSWORD')"
    [[ -n "$WEB_ADMIN_PASSWORD" ]] || { echo "WEB_ADMIN_PASSWORD is required." >&2; exit 1; }
    set_env_value WEB_ADMIN_PASSWORD "$WEB_ADMIN_PASSWORD"
else
    WEB_ADMIN_PASSWORD="$(prompt_password 'WEB_ADMIN_PASSWORD' "$WEB_ADMIN_PASSWORD")"
    [[ -n "$WEB_ADMIN_PASSWORD" ]] || { echo "WEB_ADMIN_PASSWORD is required." >&2; exit 1; }
    set_env_value WEB_ADMIN_PASSWORD "$WEB_ADMIN_PASSWORD"
fi

echo
echo "--- Please check the values you entered ---"
echo "  BOT_TOKEN:          ${BOT_TOKEN}"
echo "  ADMIN_IDS:          ${ADMIN_IDS}"
echo "  WEB_ADMIN_PASSWORD: ${WEB_ADMIN_PASSWORD}"
echo
# Give the user a moment to review before services start.
sleep 10

if ! validate_bot_token "$BOT_TOKEN"; then
    echo "BOT_TOKEN format is invalid. Get the exact token from BotFather and run the installer again." >&2
    exit 1
fi
if ! validate_admin_ids "$ADMIN_IDS"; then
    echo "ADMIN_IDS must contain numeric Telegram IDs separated by commas." >&2
    exit 1
fi

# Reload values after writing the dotenv file so validation and systemd use the same config.
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
[[ -n "${WEB_ADMIN_PASSWORD:-}" ]] || { echo "WEB_ADMIN_PASSWORD is missing from $ENV_FILE" >&2; exit 1; }
[[ -n "${BOT_TOKEN:-}" ]] || { echo "BOT_TOKEN is missing from $ENV_FILE" >&2; exit 1; }
set_default() {
    local key="$1"
    local value="$2"
    if ! grep -qE "^${key}=" "$ENV_FILE"; then
        set_env_value "$key" "$value"
    fi
}
# Detect the server address for the Web Panel link.
detect_server_ip() {
    local detected=""
    if command -v curl >/dev/null 2>&1; then
        detected="$(curl -4fsS --max-time 5 https://api.ipify.org 2>/dev/null || true)"
    fi
    if [[ -z "$detected" ]] && command -v hostname >/dev/null 2>&1; then
        detected="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
    fi
    if [[ -z "$detected" ]] && command -v ip >/dev/null 2>&1; then
        detected=$(ip route get 1.1.1.1 2>/dev/null | awk '{for (i=1; i<=NF; i++) if ($i == "src") {print $(i+1); exit}}' || true)
    fi
    printf '%s' "$detected"
}

SERVER_IP="$(detect_server_ip)"
[[ -n "$SERVER_IP" ]] || SERVER_IP="127.0.0.1"

# Bind on all interfaces so the detected server address can open the panel.
# Upgrade the old localhost default on existing installations too.
if [[ -z "${WEB_HOST:-}" || "${WEB_HOST}" == "127.0.0.1" ]]; then
    set_env_value WEB_HOST 0.0.0.0
fi
# Use browser-safe port 8090 for fresh installs and migrate previous defaults.
if [[ -z "${WEB_PORT:-}" || "${WEB_PORT}" == "8000" || "${WEB_PORT}" == "8080" || "${WEB_PORT}" == "4045" ]]; then
    set_env_value WEB_PORT 8090
fi
set_default WEB_ONLY 0
set_default WEB_WITH_BOT 1
set_default WEB_COOKIE_SECURE 0
set_default DATABASE_FILE bot.db
set_default TELEGRAM_PROXY ""
if ! grep -qE '^WEB_PUBLIC_IP=' "$ENV_FILE" || grep -qE "^WEB_PUBLIC_IP='?127\\.0\\.0\\.1'?$" "$ENV_FILE"; then
    set_env_value WEB_PUBLIC_IP "$SERVER_IP"
fi

# Reload the final values so the service message uses the actual port.
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

# Generate a secret if the project does not already have one.
if ! grep -qE '^WEB_ADMIN_SECRET=' "$ENV_FILE"; then
    set_env_value WEB_ADMIN_SECRET "$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
fi

# Create a restricted service account.
echo "[4/7] Creating service account..."
if ! id avalbot >/dev/null 2>&1; then
    useradd --system --home-dir "$INSTALL_DIR" --shell /usr/sbin/nologin avalbot
fi
chown -R avalbot:avalbot "$INSTALL_DIR"
chmod 600 "$ENV_FILE"

# Validate the installed application before registering it.
echo "[5/7] Validating Python application..."
runuser -u avalbot -- env WEB_ONLY=1 "$VENV_DIR/bin/python" -m py_compile "$INSTALL_DIR/bot.py"

# Keep Telegram polling and Web Panel in separate services. A Telegram/network
# failure must not take the admin panel offline.
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=AVAL Telegram VPN Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=avalbot
Group=avalbot
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$ENV_FILE
Environment=WEB_WITH_BOT=0
Environment=WEB_ONLY=0
ExecStart=/usr/bin/env WEB_WITH_BOT=0 WEB_ONLY=0 $VENV_DIR/bin/python $INSTALL_DIR/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

cat > "$WEB_SERVICE_FILE" <<EOF
[Unit]
Description=AVAL BOT Web Admin Panel
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=avalbot
Group=avalbot
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$ENV_FILE
Environment=WEB_WITH_BOT=0
Environment=WEB_ONLY=1
ExecStart=/usr/bin/env WEB_WITH_BOT=0 WEB_ONLY=1 $VENV_DIR/bin/python $INSTALL_DIR/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Install a narrowly-scoped privileged helper for the Web Panel.
cat > /usr/local/sbin/aval-bot-admin <<'ADMIN_HELPER'
#!/usr/bin/env bash
set -Eeuo pipefail
service_key="${1:-}"
action="${2:-}"
case "$service_key:$action" in
    bot:start|bot:stop|bot:restart) unit="aval-bot.service" ;;
    bot:remove)
        /usr/bin/systemctl disable --now aval-bot.service
        /usr/bin/rm -f /etc/systemd/system/aval-bot.service
        /usr/bin/systemctl daemon-reload
        exit 0
        ;;
    bot:status) /usr/bin/systemctl is-active aval-bot.service ; exit $? ;;
    web:status) /usr/bin/systemctl is-active aval-bot-web.service ; exit $? ;;
    web:start|web:stop|web:restart) unit="aval-bot-web.service" ;;
    *) exit 2 ;;
esac
exec /usr/bin/systemctl "$action" "$unit"
ADMIN_HELPER
chmod 755 /usr/local/sbin/aval-bot-admin
cat > /etc/sudoers.d/aval-bot-web <<SUDOERS
avalbot ALL=(root) NOPASSWD: /usr/local/sbin/aval-bot-admin
SUDOERS
chmod 440 /etc/sudoers.d/aval-bot-web
if command -v visudo >/dev/null 2>&1; then
    visudo -cf /etc/sudoers.d/aval-bot-web >/dev/null
fi

systemctl daemon-reload
systemctl enable "$SERVICE_NAME" "$WEB_SERVICE_NAME"

if [[ "$NO_START" -eq 0 ]]; then
    echo "[6/7] Starting Telegram bot and Web Panel services..."
    systemctl restart "$SERVICE_NAME" "$WEB_SERVICE_NAME"
    failed=0
    for service in "$SERVICE_NAME" "$WEB_SERVICE_NAME"; do
        for attempt in $(seq 1 10); do
            systemctl is-active --quiet "$service" && break
            sleep 1
        done
        if ! systemctl is-active --quiet "$service"; then
            echo "Service $service failed to start. Last logs:" >&2
            journalctl -u "$service" -n 80 --no-pager >&2 || true
            failed=1
        fi
    done
    for attempt in $(seq 1 10); do
        if ss -ltn 2>/dev/null | grep -qE ":${WEB_PORT}[[:space:]]"; then
            break
        fi
        sleep 1
    done
    if ! ss -ltn 2>/dev/null | grep -qE ":${WEB_PORT}[[:space:]]"; then
        echo "Web Panel is not listening on port ${WEB_PORT}. Last logs:" >&2
        journalctl -u "$WEB_SERVICE_NAME" -n 80 --no-pager >&2 || true
        failed=1
    fi
else
    echo "[6/7] Services installed but not started (--no-start)."
    failed=0
fi

# Color codes for the success banner (disabled when output is not a TTY).
if [[ -t 1 ]]; then
    C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'; C_GREEN=$'\033[0;32m'
    C_CYAN=$'\033[0;36m'; C_YELLOW=$'\033[0;33m'; C_RED=$'\033[0;31m'
else
    C_RESET=""; C_BOLD=""; C_GREEN=""; C_CYAN=""; C_YELLOW=""; C_RED=""
fi

print_success_banner() {
    echo "[7/7] Installation complete."
    echo
    echo "${C_GREEN}${C_BOLD}========================================================${C_RESET}"
    echo "${C_GREEN}${C_BOLD} AVAL BOT installed successfully${C_RESET}"
    echo "${C_GREEN}${C_BOLD}========================================================${C_RESET}"
    echo
    echo "${C_BOLD}Service status:${C_RESET}"
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo "  Telegram Bot:  ${C_GREEN}active${C_RESET}"
    else
        echo "  Telegram Bot:  ${C_RED}inactive${C_RESET}"
    fi
    if systemctl is-active --quiet "$WEB_SERVICE_NAME"; then
        echo "  Web Panel:     ${C_GREEN}active${C_RESET}"
    else
        echo "  Web Panel:     ${C_RED}inactive${C_RESET}"
    fi
    echo
    echo "${C_BOLD}Web Panel address:${C_RESET}"
    echo "  ${C_CYAN}http://${SERVER_IP}:${WEB_PORT}/admin${C_RESET}"
    echo
    echo "${C_BOLD}Terminal admin menu:${C_RESET}"
    echo "  ${C_CYAN}sudo aval-bot-menu${C_RESET}"
    echo
    echo "${C_BOLD}Quick commands:${C_RESET}"
    echo "  Status:    ${C_CYAN}sudo systemctl status $SERVICE_NAME${C_RESET}"
    echo "  Logs:      ${C_CYAN}journalctl -u $SERVICE_NAME -f${C_RESET}"
}

if [[ "$failed" -eq 0 ]]; then
    print_success_banner
    exit 0
fi

print_success_banner
echo
echo "${C_RED}${C_BOLD}One or more services are inactive.${C_RESET}"
echo "To check:"
echo "  ${C_CYAN}sudo systemctl status $SERVICE_NAME --no-pager${C_RESET}"
echo "  ${C_CYAN}sudo journalctl -u $SERVICE_NAME -n 80 --no-pager${C_RESET}"
echo "Or open the menu: ${C_CYAN}sudo aval-bot-menu${C_RESET}"
exit 1
