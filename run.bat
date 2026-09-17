@echo off
cd /d "%~dp0"
if not exist .env (
  copy /Y .env.example .env
  echo .env ساخته شد؛ BOT_TOKEN و ADMIN_IDS را داخل آن تنظیم کن.
  notepad .env
)
python -m pip install -r requirements.txt
python bot.py
pause
