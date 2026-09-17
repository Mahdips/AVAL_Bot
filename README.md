# AVAL BOT

ربات تلگرام فروش اشتراک VPN با پشتیبانی از:

- چند پنل 3x-ui
- ساخت دسته‌بندی و اتصال هر دسته به inboundهای پنل
- ساخت خودکار کانفیگ هنگام تأیید خرید یا پرداخت از کیف پول
- ساخت خودکار client و ارسال فقط لینک Subscription به‌همراه QR Code
- نمایش لینک‌های اتصال و مصرف/انقضا از پنل
- تست رایگان خودکار از پنل، با fallback به موجودی دستی
- پرداخت کارت‌به‌کارت و کیف پول
- مدیریت کاربران، موجودی دستی، آموزش، ادمین‌ها و بک‌آپ


# ===== نصب مستقیم با یک دستور از GitHub =====

## معرفی رسمی

**AVAL BOT** یک پروژهٔ متن‌باز برای مدیریت فروش اشتراک VPN در تلگرام است. این Repository مرجع رسمی پروژه است و نصب، به‌روزرسانی و مستندات از همین‌جا انجام می‌شود.

این پروژه با Python، Aiogram، FastAPI، SQLite و 3x-ui کار می‌کند و برای مدیران سرویس‌های VPN طراحی شده است.

### قابلیت‌ها

- اتصال به یک یا چند پنل 3x-ui
- مدیریت دسته‌بندی، inbound و محصولات از پنل مدیریت
- ساخت خودکار client هنگام تأیید خرید
- ارسال لینک Subscription و QR Code به کاربر
- پرداخت کارت‌به‌کارت و کیف پول
- مدیریت کاربران، سفارش‌ها، ادمین‌ها و پشتیبان‌گیری
- Web Panel مدیریت با احراز هویت
- نصب خودکار روی Ubuntu و Debian با systemd

## نصب رسمی

برای نصب رسمی، فقط دستور زیر را روی Ubuntu/Debian اجرا کنید:

```bash
curl -fsSL https://raw.githubusercontent.com/Mahdips/AVAL_Bot/main/install.sh | sudo bash
```

نصاب به‌صورت خودکار کد پروژه، وابستگی‌ها، محیط Python و سرویس `aval-bot` را نصب می‌کند. در اولین اجرا فقط `BOT_TOKEN`، `ADMIN_IDS` و `WEB_ADMIN_PASSWORD` را در ترمینال می‌پرسد. هنگام واردکردن رمز، چیزی نمایش داده نمی‌شود.

برای به‌روزرسانی نسخهٔ رسمی:

```bash
curl -fsSL https://raw.githubusercontent.com/Mahdips/AVAL_Bot/main/install.sh | sudo bash -s -- --update
```

پس از نصب، Bot و Web Panel دو سرویس مستقل هستند:

```bash
sudo systemctl status aval-bot --no-pager
sudo systemctl status aval-bot-web --no-pager
sudo journalctl -u aval-bot -f
sudo journalctl -u aval-bot-web -f
```

Web Panel برای اجرا به اتصال Telegram یا معتبر بودن `BOT_TOKEN` نیاز ندارد؛ Bot تلگرام به‌صورت جداگانه به `BOT_TOKEN` معتبر نیاز دارد.

## اطلاعات مهم نصب

- مسیر نصب: `/opt/aval-bot`
- نام سرویس بات: `aval-bot`
- نام سرویس Web Panel: `aval-bot-web`
- سرویس Web Panel مستقل از Bot اجرا می‌شود و برای نمایش صفحه به اتصال Telegram نیاز ندارد.
- Web Panel به‌صورت پیش‌فرض روی `0.0.0.0:8090` اجرا می‌شود.
- فایل تنظیمات در `/opt/aval-bot/.env` ذخیره می‌شود.
- دیتابیس در `/opt/aval-bot/bot.db` ذخیره می‌شود.
- در آپدیت، `.env` و `bot.db` قبلی حفظ می‌شوند.
- برای امنیت، پورت Web Panel را مستقیماً عمومی نکنید؛ از SSH Tunnel یا HTTPS Reverse Proxy استفاده کنید.

### اجرای پنل مدیریت از طریق SSH Tunnel

روی کامپیوتر شخصی خود اجرا کنید:

```bash
ssh -L 8090:127.0.0.1:8090 root@SERVER_IP
```

سپس در مرورگر باز کنید:

```text
http://127.0.0.1:8090/admin
```

`SERVER_IP` را با IP سرور خود جایگزین کنید.

## اتصال به 3x-ui

1. وارد Web Panel شوید.
2. بخش مدیریت پنل‌های VPN را باز کنید.
3. URL پایه، لینک Subscription نمونه و API Token پنل 3x-ui را ثبت کنید.
4. اتصال پنل را تست کنید.
5. یک category بسازید و inbound موردنظر را انتخاب کنید.
6. محصول را به category متصل کنید.

API Token پنل، Token ربات، رمزها و اطلاعات پرداخت را در Repository، Issue، Log یا چت عمومی قرار ندهید.

## اجرای دستی برای توسعه

```bash
python -m pip install -r requirements.txt
cp .env.example .env
python bot.py
```

قبل از اجرای دستی، مقادیر حساس را فقط در `.env` تنظیم کنید.

## تست پروژه

```bash
python -m pytest -q
python -m py_compile bot.py
```

## مشارکت و گزارش مشکل

این Repository مرجع رسمی پروژه است. برای پیشنهاد قابلیت، گزارش Bug یا ارسال Pull Request، از بخش Issues و Pull Requests همین Repository استفاده کنید. لطفاً قبل از ارسال، مشکل را با آخرین نسخه بررسی کنید و هیچ اطلاعات حساسی در گزارش قرار ندهید.

## مجوز استفاده

این پروژه برای استفاده و توسعهٔ شخصی/تجاری منتشر شده است. استفاده از کد با رعایت قوانین، امنیت اطلاعات کاربران و مسئولیت قانونی سرویس‌دهنده انجام می‌شود.


