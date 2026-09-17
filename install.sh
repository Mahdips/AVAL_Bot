#!/usr/bin/env bash
# AVAL BOT one-command Linux installer
set -Eeuo pipefail

INSTALL_DIR="${AVAL_BOT_INSTALL_DIR:-/opt/aval-bot}"
SERVICE_NAME="aval-bot"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
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

if [[ -n "$REPO_URL" ]]; then
    command -v curl >/dev/null 2>&1 || { echo "curl is required for GitHub installation." >&2; exit 1; }
    REMOTE_TMP="$(mktemp -d)"
    trap 'rm -rf "$REMOTE_TMP"' EXIT
    echo "Downloading AVAL BOT from GitHub..."
    curl -fsSL --retry 3 "https://codeload.github.com/${REPO_URL#https://github.com/}/tar.gz/refs/heads/${REPO_REF}" -o "$REMOTE_TMP/source.tar.gz"
    mkdir -p "$REMOTE_TMP/src"
    tar -xzf "$REMOTE_TMP/source.tar.gz" -C "$REMOTE_TMP/src"
    SOURCE_DIR="$(find "$REMOTE_TMP/src" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
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

export DEBIAN_FRONTEND=noninteractive
echo "[1/7] Installing system dependencies..."
apt-get update -y
apt-get install -y python3 python3-venv python3-pip ca-certificates curl tar

mkdir -p "$INSTALL_DIR"

# Copy application files, while never overwriting an existing database or .env.
echo "[2/7] Copying application files to $INSTALL_DIR..."
for item in bot.py requirements.txt .env.example README.md telegram-bot.service; do
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
    local label="$1"
    local current="${2:-}"
    if [[ -n "$current" ]]; then
        printf '%s already exists; keep it? [Y/n]: ' "$label"
        read -r answer </dev/tty
        if [[ ! "$answer" =~ ^[Nn]$ ]]; then
            printf '%s' "$current"
            return
        fi
    fi
    local value
    read -r -s -p "$label: " value </dev/tty
    printf '\n' >&2
    printf '%s' "$value"
}

prompt_value() {
    local label="$1"
    local current="${2:-}"
    if [[ -n "$current" ]]; then
        printf '%s already exists; keep it? [Y/n]: ' "$label"
        read -r answer </dev/tty
        if [[ ! "$answer" =~ ^[Nn]$ ]]; then
            printf '%s' "$current"
            return
        fi
    fi
    local value
    read -r -p "$label: " value </dev/tty
    printf '%s' "$value"
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

if [[ -z "${BOT_TOKEN:-}" ]]; then
    BOT_TOKEN="$(prompt_secret 'BOT_TOKEN (from BotFather)')"
    [[ -n "$BOT_TOKEN" ]] || { echo "BOT_TOKEN is required." >&2; exit 1; }
    set_env_value BOT_TOKEN "$BOT_TOKEN"
fi
if [[ -z "${ADMIN_IDS:-}" ]]; then
    ADMIN_IDS="$(prompt_value 'ADMIN_IDS (numeric Telegram IDs, comma-separated)')"
    [[ -n "$ADMIN_IDS" ]] || { echo "ADMIN_IDS is required." >&2; exit 1; }
    set_env_value ADMIN_IDS "$ADMIN_IDS"
fi
if [[ -z "${WEB_ADMIN_PASSWORD:-}" ]]; then
    WEB_ADMIN_PASSWORD="$(prompt_secret 'WEB_ADMIN_PASSWORD')"
    [[ -n "$WEB_ADMIN_PASSWORD" ]] || { echo "WEB_ADMIN_PASSWORD is required." >&2; exit 1; }
    set_env_value WEB_ADMIN_PASSWORD "$WEB_ADMIN_PASSWORD"
fi

# Reload values after writing the dotenv file so validation and systemd use the same config.
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

# Safe defaults; do not overwrite user choices.
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
set_default WEB_PORT 8000
set_default WEB_ONLY 0
set_default WEB_WITH_BOT 1
set_default WEB_COOKIE_SECURE 0
set_default DATABASE_FILE bot.db
set_default TELEGRAM_PROXY ""
if ! grep -qE '^WEB_PUBLIC_IP=' "$ENV_FILE" || grep -qE "^WEB_PUBLIC_IP='?127\\.0\\.0\\.1'?$" "$ENV_FILE"; then
    set_env_value WEB_PUBLIC_IP "$SERVER_IP"
fi

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
runuser -u avalbot -- "$VENV_DIR/bin/python" -m py_compile "$INSTALL_DIR/bot.py"

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
ExecStart=$VENV_DIR/bin/python $INSTALL_DIR/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

if [[ "$NO_START" -eq 0 ]]; then
    echo "[6/7] Starting service..."
    systemctl restart "$SERVICE_NAME"
    sleep 2
    if ! systemctl is-active --quiet "$SERVICE_NAME"; then
        echo "Service failed to start. Last logs:" >&2
        journalctl -u "$SERVICE_NAME" -n 80 --no-pager >&2 || true
        exit 1
    fi
else
    echo "[6/7] Service installed but not started (--no-start)."
fi

echo "[7/7] Installation complete."
echo "Service status: systemctl status $SERVICE_NAME"
echo "Live logs:      journalctl -u $SERVICE_NAME -f"
echo "Web panel:      http://${SERVER_IP}:8000/admin"
echo "If the panel is not reachable, allow TCP/8000 in your VPS firewall or use SSH tunneling."
