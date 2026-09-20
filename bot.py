import os
import html
import asyncio
import sqlite3
import json
import time
import re
import secrets
import uuid
import hmac
import hashlib
import socket
import subprocess
# System service operations are delegated to the fixed helper; no arbitrary commands are accepted.
from urllib.parse import quote, urlsplit, urlunsplit
from io import BytesIO
from pathlib import Path
from datetime import datetime, timedelta

import httpx
import qrcode

from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    FSInputFile,
    BufferedInputFile,
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Template
from aiogram.fsm.storage.memory import MemoryStorage

from admin_control import build_service_command, update_env_file, validate_config_updates, SERVICE_NAMES

BASE_DIR = Path(__file__).parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

app = FastAPI(title="AVAL BOT Admin")

WEB_SESSION_COOKIE = "aval_web_session"
WEB_SESSIONS = {}
WEB_SESSION_TTL = 60 * 60 * 8

WEB_ADMIN_CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;600;700;800&display=swap');
:root{--bg:#0a0d14;--bg-glow-a:#2947ff33;--bg-glow-b:#17d9c433;--glass:rgba(255,255,255,.045);--glass-strong:rgba(255,255,255,.075);--glass-border:rgba(255,255,255,.09);--glass-border-2:rgba(255,255,255,.14);--text:#eef1fb;--muted:#8992ad;--muted-2:#666f8c;--accent:#7c9eff;--accent-2:#3ddbc0;--accent-ink:#071022;--danger:#ff6b7b;--danger-ink:#2a0810;--warn:#ffb454;--radius-lg:20px;--radius-md:14px;--radius-sm:10px;--shadow-glass:0 20px 60px -20px rgba(0,0,0,.65);--blur:blur(22px);--font:'Vazirmatn',Tahoma,'Segoe UI',sans-serif}
*{box-sizing:border-box}html{color-scheme:dark}body{margin:0;min-height:100vh;font-family:var(--font);color:var(--text);background:radial-gradient(1100px 620px at 8% -8%,var(--bg-glow-a),transparent 55%),radial-gradient(900px 520px at 108% 12%,var(--bg-glow-b),transparent 50%),var(--bg);background-attachment:fixed;-webkit-font-smoothing:antialiased}
::selection{background:var(--accent);color:var(--accent-ink)}a{color:inherit}button{font-family:inherit}
::-webkit-scrollbar{width:10px;height:10px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:rgba(255,255,255,.12);border-radius:99px}::-webkit-scrollbar-thumb:hover{background:rgba(255,255,255,.2)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:6px}
.shell{display:flex;min-height:100vh}
.side{width:272px;flex-shrink:0;padding:24px 16px;position:sticky;top:0;height:100vh;border-left:1px solid var(--glass-border);background:linear-gradient(180deg,rgba(255,255,255,.05),rgba(255,255,255,.015));backdrop-filter:var(--blur);-webkit-backdrop-filter:var(--blur);display:flex;flex-direction:column;z-index:20}
.brand{display:flex;align-items:center;gap:10px;padding:6px 10px 26px;font-size:19px;font-weight:800;letter-spacing:.2px}
.brand .mark{width:34px;height:34px;border-radius:10px;display:grid;place-items:center;background:linear-gradient(145deg,var(--accent),var(--accent-2));color:var(--accent-ink);font-size:16px;font-weight:800;box-shadow:0 8px 20px -6px rgba(124,158,255,.6)}
.brand span{color:var(--muted);font-weight:600;font-size:12px;display:block;margin-top:1px}
.nav-label{color:var(--muted-2);font-size:11px;font-weight:600;margin:18px 12px 8px;letter-spacing:.3px}
nav.main-nav{display:flex;flex-direction:column;gap:3px}
nav.main-nav a{display:flex;align-items:center;gap:12px;padding:11px 13px;border-radius:var(--radius-sm);color:var(--muted);text-decoration:none;font-size:14px;font-weight:500;transition:background .15s ease,color .15s ease,transform .15s ease;position:relative}
nav.main-nav a .ic{width:18px;text-align:center;font-size:15px;opacity:.85}
nav.main-nav a:hover{background:var(--glass-strong);color:var(--text)}
nav.main-nav a.active{background:linear-gradient(90deg,rgba(124,158,255,.16),rgba(61,219,192,.08));color:var(--text);box-shadow:inset 3px 0 0 var(--accent)}
nav.main-nav a.logout{color:var(--danger);margin-top:14px}nav.main-nav a.logout:hover{background:rgba(255,107,123,.1)}
.side-foot{margin-top:auto;padding:14px 10px 4px;font-size:11px;color:var(--muted-2)}
.mobile-bar{display:none}
.main{flex:1;min-width:0;padding:30px 34px 60px;max-width:1500px}
.top{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:26px;flex-wrap:wrap}
.top h1{margin:0;font-size:25px;font-weight:800;letter-spacing:-.2px}.top .crumb{font-size:12.5px;color:var(--muted-2);margin-top:4px}
.user-chip{display:flex;align-items:center;gap:10px;padding:8px 14px 8px 8px;border-radius:99px;background:var(--glass);border:1px solid var(--glass-border);font-size:12.5px;color:var(--muted)}
.user-chip .dot{width:8px;height:8px;border-radius:50%;background:var(--accent-2);box-shadow:0 0 0 4px rgba(61,219,192,.15)}
.user-chip .avatar{width:26px;height:26px;border-radius:50%;background:linear-gradient(145deg,var(--accent),var(--accent-2));display:grid;place-items:center;font-size:12px;color:var(--accent-ink);font-weight:800}
.flash{display:flex;align-items:center;gap:10px;background:rgba(61,219,192,.1);border:1px solid rgba(61,219,192,.28);color:#bdf5ea;padding:13px 16px;border-radius:var(--radius-sm);margin-bottom:18px;font-size:13.5px}
.flash:before{content:"✓";font-weight:800}.flash.err{background:rgba(255,107,123,.1);border-color:rgba(255,107,123,.3);color:#ffd6db}.flash.err:before{content:"!"}
.card{background:var(--glass);border:1px solid var(--glass-border);border-radius:var(--radius-lg);padding:22px 22px 24px;margin-bottom:18px;backdrop-filter:var(--blur);-webkit-backdrop-filter:var(--blur);box-shadow:var(--shadow-glass)}
.card h2{margin:0 0 6px;font-size:17px;font-weight:700}.card .muted{margin:0 0 16px}.muted{color:var(--muted);font-size:13px;line-height:1.8}
.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-bottom:20px}
.stat{position:relative;overflow:hidden;background:var(--glass);border:1px solid var(--glass-border);border-radius:var(--radius-md);padding:18px 19px;backdrop-filter:var(--blur);-webkit-backdrop-filter:var(--blur)}
.stat .ic{width:32px;height:32px;border-radius:9px;display:grid;place-items:center;background:rgba(124,158,255,.14);color:var(--accent);font-size:15px;margin-bottom:14px}
.stat small{color:var(--muted);font-size:12px}.stat b{display:block;margin-top:8px;font-size:26px;font-weight:800}
.quick{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.quick a{display:flex;align-items:center;gap:10px;padding:15px 16px;border-radius:var(--radius-md);text-decoration:none;color:var(--text);background:var(--glass);border:1px solid var(--glass-border);font-size:13.5px;font-weight:600;transition:border-color .15s ease,transform .15s ease,background .15s ease}
.quick a:hover{border-color:var(--glass-border-2);background:var(--glass-strong);transform:translateY(-1px)}
.table-wrap{overflow:auto;border:1px solid var(--glass-border);border-radius:var(--radius-md)}
table{width:100%;border-collapse:collapse;min-width:680px}th,td{text-align:right;padding:13px 14px;font-size:13px;border-bottom:1px solid rgba(255,255,255,.06)}
tr:last-child td{border-bottom:0}th{color:var(--muted);font-weight:600;font-size:12px;background:rgba(255,255,255,.03);position:sticky;top:0}
tbody tr{transition:background .12s ease}tbody tr:hover{background:rgba(255,255,255,.03)}
.badge{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:99px;font-size:11.5px;font-weight:600;background:rgba(61,219,192,.14);color:#8ff2e0}
.badge:before{content:"";width:6px;height:6px;border-radius:50%;background:currentColor}.badge.off{background:rgba(255,107,123,.12);color:#ffb3bd}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:7px;border:0;border-radius:var(--radius-sm);padding:10px 17px;min-height:42px;background:linear-gradient(135deg,var(--accent),#6f8dff);color:var(--accent-ink);font-weight:700;font-size:13.5px;text-decoration:none;cursor:pointer;transition:filter .15s ease,transform .15s ease,box-shadow .15s ease;box-shadow:0 10px 24px -10px rgba(124,158,255,.55)}
.btn:hover{filter:brightness(1.07);transform:translateY(-1px)}.btn:active{transform:translateY(0)}
.btn.secondary{background:var(--glass-strong);color:var(--text);box-shadow:none;border:1px solid var(--glass-border-2)}.btn.secondary:hover{background:rgba(255,255,255,.11)}
.btn.danger{background:linear-gradient(135deg,var(--danger),#ff8a95);color:var(--danger-ink);box-shadow:0 10px 24px -10px rgba(255,107,123,.5)}
.btn.ghost{background:transparent;color:var(--muted);box-shadow:none;border:1px dashed var(--glass-border-2)}.btn.block{width:100%}.btn[disabled]{opacity:.5;cursor:not-allowed;transform:none}
.actions{display:flex;gap:9px;flex-wrap:wrap}
form.form-grid{display:grid;gap:15px;max-width:640px}
label{display:block;font-size:12.5px;color:var(--muted);font-weight:600;margin-bottom:7px}.field{display:flex;flex-direction:column}
input,select,textarea{width:100%;background:rgba(255,255,255,.035);color:var(--text);border:1px solid var(--glass-border-2);padding:12px 13px;border-radius:var(--radius-sm);font-size:13.5px;font-family:inherit;outline:none;transition:border-color .15s ease,box-shadow .15s ease,background .15s ease}
input::placeholder{color:var(--muted-2)}input:focus,select:focus,textarea:focus{border-color:var(--accent);background:rgba(124,158,255,.06);box-shadow:0 0 0 3px rgba(124,158,255,.16)}select{cursor:pointer}
.hint{font-size:11.5px;color:var(--muted-2);margin-top:6px}.form-actions{display:flex;gap:10px;margin-top:4px}
.empty{color:var(--muted);padding:34px 10px;text-align:center;font-size:13.5px;display:flex;flex-direction:column;align-items:center;gap:8px}.empty .ic{font-size:26px;opacity:.6}
pre{background:rgba(0,0,0,.28);border:1px solid var(--glass-border);padding:16px;border-radius:var(--radius-sm);line-height:2;color:#c4d0ee;overflow:auto;font-size:12.5px}
.layout-list{display:flex;flex-direction:column;gap:12px;margin-bottom:16px}.layout-row{display:flex;align-items:center;gap:8px;min-height:64px;padding:10px;border:1px dashed var(--glass-border-2);border-radius:var(--radius-sm);background:rgba(255,255,255,.02);flex-wrap:wrap}.row-label{width:72px;color:var(--muted);font-size:11px;font-weight:700}.layout-btn{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:13px 15px;border-radius:var(--radius-sm);background:var(--glass);border:1px solid var(--glass-border-2);color:var(--text);font-size:13.5px;font-weight:600;cursor:grab;user-select:none;transition:transform .18s ease,opacity .18s ease,border-color .15s ease}.layout-btn:active{cursor:grabbing}.layout-btn.dragging{opacity:.45}.layout-btn span.handle{color:var(--muted-2);font-size:15px}
.modal-overlay{position:fixed;inset:0;background:rgba(6,8,14,.6);backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px);display:none;align-items:center;justify-content:center;z-index:100;opacity:0;transition:opacity .18s ease}
.modal-overlay.show{display:flex;opacity:1}
.modal{width:min(380px,92vw);background:linear-gradient(160deg,rgba(20,24,36,.96),rgba(14,17,26,.96));border:1px solid var(--glass-border-2);border-radius:var(--radius-lg);padding:24px;box-shadow:0 30px 80px -20px rgba(0,0,0,.7);transform:translateY(10px) scale(.98);transition:transform .18s ease}
.modal-overlay.show .modal{transform:translateY(0) scale(1)}
.modal .m-ic{width:44px;height:44px;border-radius:12px;display:grid;place-items:center;background:rgba(255,107,123,.14);color:var(--danger);font-size:19px;margin-bottom:14px}
.modal h3{margin:0 0 8px;font-size:16px}.modal p{margin:0 0 20px;font-size:13px;color:var(--muted);line-height:1.8}
.modal .m-actions{display:flex;gap:10px}.modal .m-actions .btn{flex:1}
.toast-stack{position:fixed;bottom:22px;left:22px;z-index:200;display:flex;flex-direction:column;gap:10px;max-width:340px}
.toast{display:flex;align-items:flex-start;gap:10px;padding:13px 15px;border-radius:var(--radius-sm);background:linear-gradient(160deg,rgba(24,28,40,.96),rgba(16,19,28,.96));border:1px solid var(--glass-border-2);box-shadow:0 18px 46px -14px rgba(0,0,0,.6);font-size:13px;color:var(--text);transform:translateX(-120%);opacity:0;transition:transform .28s cubic-bezier(.2,.9,.3,1.2),opacity .2s ease}
.toast.show{transform:translateX(0);opacity:1}.toast .t-ic{font-size:15px;margin-top:1px}.toast.success .t-ic{color:var(--accent-2)}.toast.error .t-ic{color:var(--danger)}
.toast .t-close{margin-right:auto;cursor:pointer;color:var(--muted-2);background:none;border:0;font-size:14px}
@media(max-width:1080px){.grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:900px){.side{width:230px;padding:20px 12px}.main{padding:24px}}
@media(max-width:720px){.mobile-bar{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;position:sticky;top:0;z-index:30;background:rgba(10,13,20,.85);backdrop-filter:var(--blur);border-bottom:1px solid var(--glass-border)}.mobile-bar .brand{padding:0;font-size:16px}.mobile-bar .mark{width:28px;height:28px;font-size:13px}.burger{width:38px;height:38px;border-radius:10px;border:1px solid var(--glass-border-2);background:var(--glass);color:var(--text);font-size:16px;cursor:pointer}.shell{display:block}.side{position:fixed;inset:0 20% 0 0;height:100vh;width:auto;transform:translateX(105%);transition:transform .22s ease;border-left:1px solid var(--glass-border-2)}.side.open{transform:translateX(0)}.side-scrim{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:19}.side-scrim.show{display:block}.main{padding:18px}.grid{grid-template-columns:1fr 1fr}.quick{grid-template-columns:1fr}.top{display:block}.user-chip{display:none}form.form-grid{max-width:100%}.toast-stack{left:12px;right:12px;bottom:14px;max-width:none}}
@media(prefers-reduced-motion:reduce){*{animation-duration:.001ms !important;transition-duration:.001ms !important}}
"""

WEB_ADMIN_JS = r"""
(function(){"use strict";
function initDrawer(){var burger=document.querySelector("[data-burger]");var side=document.querySelector(".side");var scrim=document.querySelector(".side-scrim");if(!burger||!side)return;function open(){side.classList.add("open");scrim&&scrim.classList.add("show")}function close(){side.classList.remove("open");scrim&&scrim.classList.remove("show")}burger.addEventListener("click",function(){side.classList.contains("open")?close():open()});scrim&&scrim.addEventListener("click",close);side.querySelectorAll("a").forEach(function(a){a.addEventListener("click",close)})}
var stack;function ensureStack(){if(stack)return stack;stack=document.createElement("div");stack.className="toast-stack";document.body.appendChild(stack);return stack}
function showToast(message,type){if(!message)return;var s=ensureStack();var el=document.createElement("div");el.className="toast "+(type==="error"?"error":"success");var icon=type==="error"?"!":"✓";el.innerHTML='<span class="t-ic">'+icon+'</span><span>'+message+'</span><button type="button" class="t-close" aria-label="بستن">✕</button>';s.appendChild(el);requestAnimationFrame(function(){el.classList.add("show")});function remove(){el.classList.remove("show");setTimeout(function(){el.remove()},250)}el.querySelector(".t-close").addEventListener("click",remove);setTimeout(remove,4200)}
window.AvalToast=showToast;
function initFlashAsToast(){var flash=document.querySelector(".flash");if(flash)showToast(flash.textContent.trim(),flash.classList.contains("err")?"error":"success")}
function ensureModal(){var existing=document.getElementById("confirm-modal");if(existing)return existing;var overlay=document.createElement("div");overlay.className="modal-overlay";overlay.id="confirm-modal";overlay.innerHTML='<div class="modal"><div class="m-ic">!</div><h3 id="confirm-title">حذف این مورد؟</h3><p id="confirm-body">این عملیات قابل بازگشت نیست.</p><div class="m-actions"><button type="button" class="btn secondary" data-cancel>انصراف</button><button type="button" class="btn danger" data-confirm>حذف کن</button></div></div>';document.body.appendChild(overlay);return overlay}
function initDeleteModals(){var forms=document.querySelectorAll("form[data-confirm-delete]");if(!forms.length)return;var overlay=ensureModal();var titleEl=overlay.querySelector("#confirm-title");var bodyEl=overlay.querySelector("#confirm-body");var cancelBtn=overlay.querySelector("[data-cancel]");var confirmBtn=overlay.querySelector("[data-confirm]");var pendingForm=null;function close(){overlay.classList.remove("show");pendingForm=null}forms.forEach(function(form){form.addEventListener("submit",function(e){if(form.dataset.confirmed==="1")return;e.preventDefault();pendingForm=form;titleEl.textContent=form.getAttribute("data-confirm-title")||"حذف این مورد؟";bodyEl.textContent=form.getAttribute("data-confirm-delete")||"این عملیات قابل بازگشت نیست.";overlay.classList.add("show")})});cancelBtn.addEventListener("click",close);overlay.addEventListener("click",function(e){if(e.target===overlay)close()});document.addEventListener("keydown",function(e){if(e.key==="Escape")close()});confirmBtn.addEventListener("click",function(){if(!pendingForm)return;pendingForm.dataset.confirmed="1";pendingForm.requestSubmit?pendingForm.requestSubmit():pendingForm.submit();close()})}
function initHomeLayoutDrag(){var box=document.getElementById("layout");if(!box)return;var dragEl=null;box.querySelectorAll(".layout-row").forEach(function(row){row.addEventListener("dragover",function(e){e.preventDefault();if(e.dataTransfer)e.dataTransfer.dropEffect="move"});row.addEventListener("drop",function(e){e.preventDefault();var target=e.target.closest(".layout-btn");if(!dragEl||target===dragEl)return;if(target&&target.parentNode===row){var rect=target.getBoundingClientRect();row.insertBefore(dragEl,(e.clientY-rect.top)>rect.height/2?target.nextSibling:target)}else{row.appendChild(dragEl)}})});box.querySelectorAll(".layout-btn").forEach(function(btn){btn.addEventListener("dragstart",function(e){dragEl=btn;if(e.dataTransfer){e.dataTransfer.effectAllowed="move";e.dataTransfer.setData("text/plain",btn.dataset.key||"")}btn.classList.add("dragging")});btn.addEventListener("dragend",function(){btn.classList.remove("dragging");dragEl=null})})}
function initPasswordToggles(){document.querySelectorAll("input[type=password]").forEach(function(input){var button=document.createElement("button");button.type="button";button.className="btn secondary";button.style.marginTop="8px";button.textContent="نمایش رمز";button.addEventListener("click",function(){var visible=input.type==="text";input.type=visible?"password":"text";button.textContent=visible?"نمایش رمز":"مخفی‌کردن رمز"});input.parentNode.appendChild(button)})}
document.addEventListener("DOMContentLoaded",function(){initDrawer();initFlashAsToast();initDeleteModals();initHomeLayoutDrag();initPasswordToggles()});
})();
"""

WEB_ADMIN_HTML = ("""
<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }} | AVAL BOT</title><style>__CSS__</style></head><body>
<div class="mobile-bar"><div class="brand"><span class="mark">A</span> AVAL <span style="color:var(--muted)">BOT</span></div><button class="burger" data-burger aria-label="منو">☰</button></div>
<div class="side-scrim"></div>
<div class="shell">
<aside class="side"><div class="brand"><span class="mark">A</span><div>AVAL <span>پنل مدیریت</span></div></div>
<div class="nav-label">مدیریت سامانه</div>
<nav class="main-nav">{% for key,label,icon in nav %}<a href="/admin?section={{key}}" class="{% if section==key %}active{% endif %}"><span class="ic">{{icon}}</span>{{label}}</a>{% endfor %}<a href="/admin/logout" class="logout"><span class="ic">⏻</span>خروج</a></nav>
<div class="side-foot">AVAL BOT Admin</div>
</aside>
<main class="main"><div class="top"><div><h1>{{ title }}</h1><div class="crumb">مدیریت / {{ title }}</div></div><div class="user-chip"><div class="avatar">A</div><span class="dot"></span> پنل مدیریت امن</div></div>
{% if flash %}<div class="flash">{{flash}}</div>{% endif %}
{{ body|safe }}
</main></div>
<script>__JS__</script>
</body></html>
""").replace("__CSS__", WEB_ADMIN_CSS).replace("__JS__", WEB_ADMIN_JS)

WEB_NAV = [("dashboard", "نمای کلی", "🏠"), ("runtime", "کنترل Bot و تنظیمات", "⚙️"), ("panels", "زیرساخت پنل‌ها", "🌐"), ("products", "ساخت و مدیریت Config", "🛍"), ("home", "جایگذاری دکمه‌های Bot", "🧩"), ("users", "کاربران", "👥")]

def web_render(section, title, body, request, flash=None):
    return HTMLResponse(Template(WEB_ADMIN_HTML).render(nav=WEB_NAV, section=section, title=title, body=body, flash=flash or request.query_params.get("flash") or request.cookies.get("aval_flash")))

def web_guard(request):
    token=request.cookies.get(WEB_SESSION_COOKIE)
    record=WEB_SESSIONS.get(token)
    if not record or record["expires"] < time.time():
        if token: WEB_SESSIONS.pop(token, None)
        return False
    return True


def web_login_page(error=""):
    return HTMLResponse("""<!doctype html><html lang='fa' dir='rtl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>ورود مدیریت | AVAL BOT</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;600;700;800&display=swap');
:root{--bg:#0a0d14;--glass:rgba(255,255,255,.045);--glass-border-2:rgba(255,255,255,.14);--text:#eef1fb;--muted:#8992ad;--accent:#7c9eff;--accent-2:#3ddbc0;--accent-ink:#071022;--danger:#ff6b7b;--radius-lg:20px;--radius-sm:10px}
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;font-family:'Vazirmatn',Tahoma,sans-serif;color:var(--text);background:radial-gradient(1100px 620px at 8% -8%,#2947ff33,transparent 55%),radial-gradient(900px 520px at 108% 12%,#17d9c433,transparent 50%),var(--bg)}
.login-box{width:min(380px,92vw);background:var(--glass);border:1px solid var(--glass-border-2);border-radius:var(--radius-lg);padding:32px 28px;backdrop-filter:blur(22px);-webkit-backdrop-filter:blur(22px);box-shadow:0 20px 60px -20px rgba(0,0,0,.65)}
.mark{width:46px;height:46px;border-radius:13px;display:grid;place-items:center;background:linear-gradient(145deg,var(--accent),var(--accent-2));color:var(--accent-ink);font-weight:800;font-size:19px;margin-bottom:18px}
.login-box h2{margin:0 0 6px;font-size:19px}.login-box p{margin:0 0 22px;color:var(--muted);font-size:13px}
label{display:block;font-size:12.5px;color:var(--muted);font-weight:600;margin-bottom:7px}
input{width:100%;background:rgba(255,255,255,.035);color:var(--text);border:1px solid var(--glass-border-2);padding:12px 13px;border-radius:var(--radius-sm);font-size:13.5px;font-family:inherit;outline:none}
input:focus{border-color:var(--accent);background:rgba(124,158,255,.06);box-shadow:0 0 0 3px rgba(124,158,255,.16)}
button{width:100%;margin-top:16px;border:0;border-radius:var(--radius-sm);padding:12px;min-height:44px;background:linear-gradient(135deg,var(--accent),#6f8dff);color:var(--accent-ink);font-weight:700;font-size:13.5px;cursor:pointer}
button:hover{filter:brightness(1.07)}
.err-box{margin-top:14px;background:rgba(255,107,123,.1);border:1px solid rgba(255,107,123,.3);color:#ffd6db;padding:11px 14px;border-radius:var(--radius-sm);font-size:12.5px}
</style></head><body>
<form class='login-box' method='post' action='/admin/login'>
<div class='mark'>A</div>
<h2>ورود به مدیریت AVAL BOT</h2>
<p>رمز پنل را وارد کنید.</p>
<label>رمز عبور</label>
<input name='password' type='password' required autofocus placeholder='••••••••'>
<button type='button' id='toggle-login-password' style='width:100%;margin-top:10px;background:transparent;color:var(--muted);border:1px solid var(--glass-border-2);border-radius:var(--radius-sm);padding:10px;cursor:pointer'>نمایش رمز</button>
<button>ورود</button>
<script>document.getElementById('toggle-login-password').addEventListener('click',function(){var input=document.querySelector("input[name=password]");var visible=input.type==='text';input.type=visible?'password':'text';this.textContent=visible?'نمایش رمز':'مخفی‌کردن رمز'})</script>
""" + (f"<div class='err-box'>{error}</div>" if error else "") + """
</form></body></html>""")

@app.get("/", response_class=HTMLResponse)
async def web_root():
    return RedirectResponse("/admin", status_code=307)

@app.post("/admin/runtime/{service}/{action}")
async def web_runtime_service(service: str, action: str, request: Request):
    if not web_guard(request):
        return RedirectResponse("/admin", status_code=303)
    try:
        command = build_service_command(service, action)
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
        ok = result.returncode == 0
    except (ValueError, OSError, subprocess.SubprocessError):
        ok = False
    message = "عملیات با موفقیت انجام شد." if ok else "عملیات انجام نشد؛ وضعیت دسترسی systemd را بررسی کن."
    return RedirectResponse(f"/admin?section=runtime&flash={quote(message)}", status_code=303)


@app.post("/admin/runtime/config")
async def web_runtime_config(request: Request):
    if not web_guard(request):
        return RedirectResponse("/admin", status_code=303)
    form = await request.form()
    bot_token = str(form.get("bot_token") or "").strip()
    admin_ids = str(form.get("admin_ids") or "").strip()
    password = str(form.get("web_password") or "")
    password_again = str(form.get("web_password_again") or "")
    if bot_token and len(bot_token) < 10:
        return RedirectResponse("/admin?section=runtime&flash=" + quote("Bot Token واردشده معتبر نیست."), status_code=303)
    if password or password_again:
        if password != password_again or len(password) < 8:
            return RedirectResponse("/admin?section=runtime&flash=" + quote("رمزها برابر نیستند یا کمتر از ۸ کاراکتر هستند."), status_code=303)
    updates = {}
    if bot_token:
        updates["BOT_TOKEN"] = bot_token
    if admin_ids:
        updates["ADMIN_IDS"] = admin_ids
    if password:
        updates["WEB_ADMIN_PASSWORD"] = password
    if not updates:
        return RedirectResponse("/admin?section=runtime&flash=" + quote("تغییری برای ذخیره وارد نشده است."), status_code=303)
    try:
        validate_config_updates(updates)
        update_env_file(ENV_FILE, updates)
    except (ValueError, OSError):
        return RedirectResponse("/admin?section=runtime&flash=" + quote("تنظیمات معتبر نیست یا ذخیرهسازی انجام نشد."), status_code=303)
    restarted = []
    failed = False
    for service_key in ("bot", "web"):
        try:
            result = subprocess.run(build_service_command(service_key, "restart"), capture_output=True, timeout=20)
            if result.returncode == 0:
                restarted.append(service_key)
            else:
                failed = True
        except (OSError, subprocess.SubprocessTimeoutExpired):
            failed = True
    if failed and not restarted:
        return RedirectResponse("/admin?section=runtime&flash=" + quote("تنظیمات ذخیره شد ولی restart سرویس‌ها ناموفق بود؛ دسترسی sudoers را بررسی کن."), status_code=303)
    if failed:
        return RedirectResponse("/admin?section=runtime&flash=" + quote("تنظیمات ذخیره شد؛ بعضی سرویس‌ها restart شدند ولی همه موفق نبودند."), status_code=303)
    return RedirectResponse("/admin?section=runtime&flash=" + quote("تنظیمات ذخیره شد و سرویس‌ها برای اعمال تغییرات restart شدند."), status_code=303)


@app.post("/admin/runtime/delete-bot")
async def web_runtime_delete_bot(request: Request):
    if not web_guard(request):
        return RedirectResponse("/admin", status_code=303)
    try:
        subprocess.run(["sudo", "-n", "/usr/local/sbin/aval-bot-admin", "bot", "remove"], capture_output=True, timeout=20, check=False)
        message = "سرویس Bot حذف شد؛ Web Panel و دیتابیس دست‌نخورده باقی ماندند."
    except (OSError, subprocess.SubprocessError):
        message = "حذف سرویس Bot انجام نشد."
    return RedirectResponse("/admin?section=runtime&flash=" + quote(message), status_code=303)


@app.get("/admin", response_class=HTMLResponse)
async def web_admin(request: Request):
    if not web_guard(request): return web_login_page()
    section=request.query_params.get("section","dashboard")
    connection=get_db()
    stats={"users":connection.execute("select count(*) from users").fetchone()[0],"products":connection.execute("select count(*) from products where active=1 and category_id is not null").fetchone()[0],"panels":connection.execute("select count(*) from xui_panels where active=1").fetchone()[0],"orders":connection.execute("select count(*) from orders where status='approved'").fetchone()[0]}
    if section=="runtime":
        service_rows = []
        for service_key, service_label in (("bot", "ربات تلگرام"), ("web", "وب‌پنل")):
            try:
                result = subprocess.run(["sudo", "-n", "/usr/local/sbin/aval-bot-admin", service_key, "status"], capture_output=True, text=True, timeout=5)
                active = result.returncode == 0 and result.stdout.strip() == "active"
            except (OSError, subprocess.SubprocessError):
                active = False
            service_rows.append({"key": service_key, "label": service_label, "active": active})
        env_values = {}
        if ENV_FILE.exists():
            for line in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    key, value = line.split("=", 1)
                    env_values[key.strip()] = value.strip().strip("'").strip('"')
        masked_token = "تنظیم شده (مخفی)" if env_values.get("BOT_TOKEN") else "تنظیم نشده"
        masked_password = "تنظیم شده (مخفی)" if env_values.get("WEB_ADMIN_PASSWORD") else "تنظیم نشده"
        masked_ids = "تنظیم شده (مخفی)" if env_values.get("ADMIN_IDS") else "تنظیم نشده"
        body = Template("""<div class='card'><h2>کنترل سرویس‌ها</h2><p class='muted'>از این بخش می‌توانی Bot و Web Panel را مستقل کنترل کنی.</p><div class='table-wrap'><table><tr><th>سرویس</th><th>وضعیت</th><th>عملیات</th></tr>{% for s in services %}<tr><td>{{s['label']}}</td><td>{% if s['active'] %}<span class='badge'>فعال</span>{% else %}<span class='badge off'>متوقف</span>{% endif %}</td><td><div class='actions'><form method='post' action='/admin/runtime/{{s['key']}}/start'><button class='btn secondary'>Start</button></form><form method='post' action='/admin/runtime/{{s['key']}}/stop'><button class='btn danger'>Stop</button></form><form method='post' action='/admin/runtime/{{s['key']}}/restart'><button class='btn'>Restart</button></form>{% if s['key']=='bot' %}<form method='post' action='/admin/runtime/delete-bot' onsubmit="return confirm('سرویس Bot حذف شود؟ Web Panel و دیتابیس حفظ می‌شوند.')"><button class='btn danger'>حذف Bot</button></form>{% endif %}</div></td></tr>{% endfor %}</table></div></div><div class='card'><h2>تنظیمات نصب</h2><p class='muted'>مقدارهای حساس نمایش داده نمی‌شوند. رمزها قابل مشاهده نیستند؛ فقط می‌توانی آن‌ها را تغییر بدهی.</p><div class='table-wrap'><table><tr><th>تنظیم</th><th>مقدار امن</th></tr><tr><td>BOT_TOKEN</td><td><code>{{token}}</code></td></tr><tr><td>ADMIN_IDS</td><td><code>{{ids}}</code></td></tr><tr><td>WEB_ADMIN_PASSWORD</td><td>{{password}}</td></tr></table></div><h3>تغییر تنظیمات</h3><form method='post' action='/admin/runtime/config' class='form-grid'><div class='field'><label>Bot Token جدید (خالی = بدون تغییر)</label><input name='bot_token' type='password' data-reveal autocomplete='new-password'></div><div class='field'><label>Admin IDs جدید (مثلاً 123,456؛ خالی = بدون تغییر)</label><input name='admin_ids' inputmode='numeric'></div><div class='field'><label>رمز Web Panel جدید (خالی = بدون تغییر)</label><input name='web_password' type='password' data-reveal autocomplete='new-password' minlength='8'></div><div class='field'><label>تکرار رمز جدید</label><input name='web_password_again' type='password' data-reveal autocomplete='new-password' minlength='8'></div><div class='form-actions'><button class='btn'>ذخیره و اعمال</button></div></form></div>""").render(services=service_rows, token=masked_token, ids=masked_ids, password=masked_password)
        title="کنترل Bot و تنظیمات"
    elif section=="panels":
        rows=connection.execute("select id,name,base_url,active,subscription_url,api_token from xui_panels order by id desc").fetchall()
        body=Template("""<div class='card'><h2>مدیریت پنل‌های 3x-ui</h2><p class='muted'>افزودن، ویرایش، تست اتصال، inboundها و حذف پنل از همین بخش انجام می‌شود.</p><div class='actions'><a class='btn' href='/admin/panel/new'>＋ افزودن پنل</a><a class='btn secondary' href='/admin/category/new'>＋ افزودن دسته و انتخاب inbound</a><a class='btn secondary' href='/admin?section=panel-status'>📡 وضعیت و سلامت پنل‌ها</a></div></div>""" + "<div class='card'>" + "{{ table }}" + "</div>").render(table=Template("""{% if rows %}<div class='table-wrap'><table><tr><th>نام</th><th>آدرس</th><th>Subscription</th><th>وضعیت</th><th>عملیات</th></tr>{% for r in rows %}<tr><td>{{r['name']}}</td><td>{{r['base_url']}}</td><td>{% if r['subscription_url'] %}<span class='badge'>ثبت شده</span>{% else %}<span class='badge off'>ثبت نشده</span>{% endif %}</td><td>{% if r['active'] %}<span class='badge'>فعال</span>{% else %}<span class='badge off'>غیرفعال</span>{% endif %}</td><td><div class='actions'><a class='btn secondary' href='/admin/panel/{{r['id']}}'>مدیریت</a><a class='btn secondary' href='/admin/panel/{{r['id']}}/edit'>ویرایش</a><form method='post' action='/admin/panel/{{r['id']}}/delete' onsubmit="return confirm('این پنل و اتصال‌های وابسته غیرفعال شوند؟')"><button class='btn danger'>حذف</button></form></div></td></tr>{% endfor %}</table></div>{% else %}<div class='empty'><div class='ic'>🌐</div>هنوز پنلی ثبت نشده است.</div>{% endif %}""").render(rows=rows)); title="پنل‌های 3x-ui"
    elif section=="products":
        rows=connection.execute("select products.*, categories.name as category_name from products left join categories on categories.id=products.category_id where products.category_id is not null order by products.id desc").fetchall()
        body=Template("""<div class='card'><h2>ساخت و مدیریت Config</h2><p class='muted'>این تب فقط محصولات پنلی را مدیریت می‌کند؛ موجودی دستی و کانفیگ انباری در فروش استفاده نمی‌شود.</p><div class='actions'><a class='btn' href='/admin/product/new'>＋ ساخت محصول پنلی</a><a class='btn secondary' href='/admin/test'>تنظیم سرویس تست</a></div></div><div class='card'>{% if rows %}<div class='table-wrap'><table><tr><th>نام</th><th>مدت</th><th>حجم</th><th>قیمت</th><th>دسته / مدل inbound</th><th>وضعیت</th><th>عملیات</th></tr>{% for r in rows %}<tr><td>{{r['name']}}</td><td>{{r['duration_days']}} روز</td><td>{{r['volume_gb']}} GB</td><td>{{r['price']}}</td><td>{{r['category_name'] or '—'}}</td><td>{% if r['active'] %}<span class='badge'>فعال</span>{% else %}<span class='badge off'>غیرفعال</span>{% endif %}</td><td><div class='actions'><a class='btn secondary' href='/admin/product/{{r['id']}}/edit'>✏️ ویرایش</a><form method='post' action='/admin/product/{{r['id']}}/delete' onsubmit="return confirm('محصول حذف شود؟ سفارش‌های قبلی حفظ می‌شوند.')"><button class='btn danger'>حذف</button></form></div></td></tr>{% endfor %}</table></div>{% else %}<div class='empty'><div class='ic'>🛍</div>هنوز محصولی ساخته نشده است.</div>{% endif %}</div>""").render(rows=rows); title="ساخت و مدیریت Config"
    elif section=="public-products":
        rows=connection.execute("select products.*, categories.name as category_name from products join categories on categories.id=products.category_id join xui_panels on xui_panels.id=categories.panel_id where products.active=1 and categories.active=1 and xui_panels.active=1 order by products.id desc").fetchall()
        body=Template("""<div class='card'><h2>محصولات قابل نمایش برای کاربر</h2><p class='muted'>فقط محصولاتی که کاربر می‌تواند ببیند و بخرد؛ همه از پنل 3x-ui ساخته می‌شوند.</p><div class='table-wrap'><table><tr><th>نام</th><th>مدت</th><th>حجم</th><th>قیمت</th><th>مدل پنل</th></tr>{% for r in rows %}<tr><td>{{r['name']}}</td><td>{{r['duration_days']}} روز</td><td>{{r['volume_gb']}} GB</td><td>{{r['price']}}</td><td>{{r['category_name']}}</td></tr>{% else %}<tr><td colspan='5'>محصول فعالی برای فروش وجود ندارد.</td></tr>{% endfor %}</table></div></div>""").render(rows=rows); title="محصولات قابل نمایش برای کاربر"
    elif section=="panel-status":
        rows=connection.execute("select id,name,base_url,active,subscription_url,api_token from xui_panels order by id desc").fetchall()
        status_rows=[]
        for panel in rows:
            try:
                snapshot=await fetch_panel_status(dict(panel))
            except Exception:
                snapshot={"reachable": False, "latency_ms": None, "api": "offline", "server_status": None, "inbounds": [], "error": "بررسی وضعیت پنل با خطای داخلی مواجه شد."}
            status_rows.append({"panel": panel, "status": snapshot, "text": panel_status_text(panel, snapshot)})
        body=Template("""<div class='card'><h2>وضعیت و سلامت پنل‌ها</h2><p class='muted'>Ping شبکه، دسترسی پایه و اطلاعات عمومی سلامت نمایش داده می‌شود؛ API Token هرگز نمایش داده نمی‌شود.</p></div><div class='card'><div class='table-wrap'><table><tr><th>پنل</th><th>آدرس</th><th>وضعیت سرور</th><th>Ping</th><th>API</th><th>جزئیات</th></tr>{% for item in rows %}<tr><td>{{item['panel']['name']}}</td><td>{{item['panel']['base_url']}}</td><td>{% if item['status']['reachable'] %}<span class='badge'>آنلاین</span>{% else %}<span class='badge off'>آفلاین</span>{% endif %}</td><td>{{item['status']['latency_ms'] or '—'}} {% if item['status']['latency_ms'] %}ms{% endif %}</td><td>{{item['status']['api']}}</td><td>{{item['status']['error'] or 'اتصال TCP برقرار است'}}</td></tr>{% else %}<tr><td colspan='6'>پنلی ثبت نشده است.</td></tr>{% endfor %}</table></div></div>""").render(rows=status_rows); title="وضعیت پنل‌ها"
    elif section=="users":
        rows=connection.execute("select * from users order by id desc").fetchall()
        body=Template("""<div class='card'><h2>مدیریت کاربران</h2>{% if rows %}<div class='table-wrap'><table><tr><th>تلگرام</th><th>نام کاربری</th><th>نام</th><th>موجودی</th><th>عملیات</th></tr>{% for r in rows %}<tr><td>{{r['telegram_id']}}</td><td>{{r['username'] or '—'}}</td><td>{{r['first_name'] or '—'}}</td><td>{{r['balance']}}</td><td><a class='btn secondary' href='/admin/user/{{r['telegram_id']}}'>مشاهده و مدیریت</a></td></tr>{% endfor %}</table></div>{% else %}<div class='empty'><div class='ic'>👥</div>کاربری ثبت نشده است.</div>{% endif %}</div>""").render(rows=rows); title="کاربران"
    elif section=="home":
        layout=get_home_layout()
        rows=home_layout_rows(layout)
        body=Template("""<div class='card'><h2>جایگذاری دقیق دکمه‌های Bot</h2><p class='muted'>هر ردیف را جداگانه می‌بینی. دکمه‌ها را بکش و دقیقاً در جای دلخواه همان ردیف یا بین ردیف‌ها رها کن.</p><form method='post' action='/admin/home-layout' onsubmit="document.getElementById('rows').value=[...document.querySelectorAll('.layout-row')].map(function(row){return [...row.querySelectorAll('.layout-btn')].map(function(x){return x.dataset.key}).join(',')}).filter(Boolean).join('|')"><div id='layout' class='layout-list'>{% for row in rows %}<div class='layout-row' data-row><div class='row-label'>ردیف {{loop.index}}</div>{% for key in row %}<button type='button' class='layout-btn' draggable='true' data-key='{{key}}'>{{labels[key]}} <span class='handle'>↕</span></button>{% endfor %}</div>{% endfor %}</div><input type='hidden' id='rows' name='rows'><div class='field' style='max-width:220px'><label>تعداد ستون پیش‌فرض</label><select name='columns'><option value='1' {% if columns==1 %}selected{% endif %}>۱</option><option value='2' {% if columns==2 %}selected{% endif %}>۲</option><option value='3' {% if columns==3 %}selected{% endif %}>۳</option></select></div><div class='form-actions' style='margin-top:14px'><button class='btn'>ذخیره جایگذاری</button></div></form></div>""").render(rows=rows, labels=HOME_BUTTONS, columns=layout['columns']); title="جایگذاری دکمه‌های Bot"
    else: body=Template("""<div class='grid'>{% for k,v in stats.items() %}<div class='stat'><div class='ic'>{% if k=='users' %}👥{% elif k=='products' %}🛍{% elif k=='panels' %}🌐{% else %}✅{% endif %}</div><small>{{{'users':'کاربران','products':'محصولات فعال','panels':'پنل‌های فعال','orders':'اشتراک‌های تحویل‌شده'}[k]}}</small><b>{{v}}</b></div>{% endfor %}</div><div class='card'><h2>دسترسی سریع</h2><div class='quick'><a href='/admin?section=panels'>🌐 مدیریت پنل‌های 3x-ui</a><a href='/admin?section=products'>🛍 مدیریت محصولات پنلی</a><a href='/admin?section=users'>👥 مدیریت کاربران</a></div></div><div class='card'><h2>وضعیت سامانه</h2><p class='muted'>همه محصولات جدید فقط از پنل 3x-ui ساخته و تحویل می‌شوند. موجودی دستی از مسیر فروش حذف شده است.</p></div>""").render(stats=stats); title="نمای کلی"
    connection.close(); return web_render(section,title,body,request)

@app.post("/admin/login")
async def web_login(request: Request):
    form=await request.form(); password=str(form.get("password") or "")
    expected=os.getenv("WEB_ADMIN_PASSWORD", "")
    if expected and secrets.compare_digest(password, expected):
        token=secrets.token_urlsafe(32); WEB_SESSIONS[token]={"expires": time.time()+WEB_SESSION_TTL}
        response=RedirectResponse("/admin",status_code=303); response.set_cookie(WEB_SESSION_COOKIE, token, httponly=True, samesite="strict", secure=os.getenv("WEB_COOKIE_SECURE","0")=="1", max_age=WEB_SESSION_TTL); return response
    return web_login_page("رمز نادرست است یا WEB_ADMIN_PASSWORD تنظیم نشده.")

@app.get("/admin/panel/new", response_class=HTMLResponse)
def web_panel_new(request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    return web_render("panels", "افزودن پنل", """<div class='card'><h2>افزودن پنل 3x-ui</h2><form method='post' class='form-grid'><div class='field'><label>نام پنل</label><input name='name' required placeholder='مثلاً پنل آلمان ۱'></div><div class='field'><label>آدرس پنل</label><input name='base_url' placeholder='https://panel.example' required></div><div class='field'><label>لینک Subscription نمونه</label><input name='subscription_url' required></div><div class='field'><label>API Token</label><input name='api_token' type='password' required></div><div class='form-actions'><button class='btn'>ذخیره پنل</button><a href='/admin?section=panels' class='btn secondary'>انصراف</a></div></form></div>""", request)

@app.post("/admin/panel/new")
async def web_panel_create(request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    form=await request.form(); name=str(form.get("name") or "").strip(); base_url=normalize_xui_base_url(str(form.get("base_url") or "").strip()); subscription_url=str(form.get("subscription_url") or "").strip(); api_token=str(form.get("api_token") or "").strip()
    if not name or not base_url or not subscription_url or not api_token: return web_render("panels","افزودن پنل","<div class='card'>همه فیلدها الزامی هستند.</div>",request)
    try:
        con=get_db(); con.execute("insert into xui_panels(name,base_url,subscription_url,api_token,active,created_at) values(?,?,?,?,1,?)",(name,base_url,subscription_url,api_token,now_text())); con.commit(); con.close()
    except sqlite3.IntegrityError:
        return web_render("panels", "افزودن پنل", "<div class='card'>پنلی با این نام قبلاً ثبت شده است.</div>", request)
    return RedirectResponse("/admin?section=panels",status_code=303)

@app.get("/admin/panel/{panel_id}/edit", response_class=HTMLResponse)
async def web_panel_edit(panel_id: int, request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    con=get_db(); panel=con.execute("select id,name,base_url,subscription_url,active from xui_panels where id=?", (panel_id,)).fetchone(); con.close()
    if not panel: return web_render("panels", "پنل پیدا نشد", "<div class='card'>پنل وجود ندارد.</div>", request)
    body=Template("""<div class='card'><h2>ویرایش پنل</h2><p class='muted'>API Token برای امنیت قابل مشاهده نیست؛ اگر خالی بماند، همان مقدار قبلی حفظ می‌شود.</p><form method='post' class='form-grid'><div class='field'><label>نام پنل</label><input name='name' value='{{p['name']}}' required></div><div class='field'><label>آدرس پنل</label><input name='base_url' value='{{p['base_url']}}' required></div><div class='field'><label>لینک Subscription نمونه</label><input name='subscription_url' value='{{p['subscription_url'] or ''}}' required></div><div class='field'><label>API Token جدید (اختیاری)</label><input name='api_token' type='password' placeholder='بدون تغییر'></div><div class='field'><label>وضعیت</label><select name='active'><option value='1' {% if p['active'] %}selected{% endif %}>فعال</option><option value='0' {% if not p['active'] %}selected{% endif %}>غیرفعال</option></select></div><div class='form-actions'><button class='btn'>ذخیره تغییرات</button><a href='/admin?section=panels' class='btn secondary'>انصراف</a></div></form></div>""").render(p=panel)
    return web_render("panels", "ویرایش پنل", body, request)

@app.post("/admin/panel/{panel_id}/edit")
async def web_panel_edit_save(panel_id: int, request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    form=await request.form(); name=str(form.get("name") or "").strip(); base_url=str(form.get("base_url") or "").strip(); sub=str(form.get("subscription_url") or "").strip(); token=str(form.get("api_token") or ""); active=1 if str(form.get("active")) == "1" else 0
    if not name or not base_url or not sub: return web_render("panels", "ویرایش پنل", "<div class='card'>نام، آدرس و لینک Subscription الزامی است.</div>", request)
    con=get_db()
    if token: con.execute("update xui_panels set name=?,base_url=?,subscription_url=?,api_token=?,active=? where id=?", (name,normalize_xui_base_url(base_url),sub,token,active,panel_id))
    else: con.execute("update xui_panels set name=?,base_url=?,subscription_url=?,active=? where id=?", (name,normalize_xui_base_url(base_url),sub,active,panel_id))
    con.commit(); con.close(); return RedirectResponse("/admin?section=panels", status_code=303)

@app.get("/admin/panel/{panel_id}", response_class=HTMLResponse)
async def web_panel_detail(panel_id: int, request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    con=get_db(); panel=con.execute("select * from xui_panels where id=?",(panel_id,)).fetchone(); cats=con.execute("select * from categories where panel_id=? order by id",(panel_id,)).fetchall(); con.close()
    if not panel: return web_render("panels","پنل پیدا نشد","<div class='card'>پنل وجود ندارد.</div>",request)
    category_rows = []
    for category in cats:
        category_rows.append({"row": category, "inbound_ids": ", ".join(map(str, category_inbound_ids(category))) or "—"})
    body=Template("""<div class='card'><h2>{{p['name']}}</h2><p class='muted'>آدرس: {{p['base_url']}}</p><p style='font-size:13px;margin:0 0 16px'>لینک Subscription: {% if p['subscription_url'] %}<span class='badge'>ثبت شده</span>{% else %}<span class='badge off'>ثبت نشده</span>{% endif %}</p><div class='actions'><a class='btn' href='/admin/panel/{{p['id']}}/category/new'>＋ افزودن دسته و تنظیم inbound</a><form method='post' action='/admin/panel/{{p['id']}}/test'><button class='btn secondary'>تست اتصال</button></form><form method='post' action='/admin/panel/{{p['id']}}/delete' data-confirm-delete="اطلاعات این پنل حذف می‌شود. ادامه می‌دهید؟" data-confirm-title="حذف پنل"><button class='btn danger'>حذف پنل</button></form></div></div><div class='card'><h2>Inbound / دسته‌بندی‌ها</h2>{% if cats %}<div class='table-wrap'><table><tr><th>نام</th><th>Inbound IDها</th><th>وضعیت</th><th>عملیات</th></tr>{% for item in cats %}{% set c=item['row'] %}<tr><td>{{c['name']}}</td><td>{{item['inbound_ids']}}</td><td>{% if c['active'] %}<span class='badge'>فعال</span>{% else %}<span class='badge off'>غیرفعال</span>{% endif %}</td><td><div class='actions'>{% if c['active'] %}<a class='btn secondary' href='/admin/category/{{c['id']}}/edit'>ویرایش inbound</a><form method='post' action='/admin/category/{{c['id']}}/delete' data-confirm-delete="این دسته و اتصال محلی آن حذف می‌شود. ادامه می‌دهید؟" data-confirm-title="حذف دسته"><button class='btn danger'>حذف</button></form>{% endif %}</div></td></tr>{% endfor %}</table></div>{% else %}<div class='empty'><div class='ic'>📁</div>دسته‌ای برای این پنل ثبت نشده است.</div>{% endif %}</div>""").render(p=panel,cats=category_rows)
    return web_render("panels", "مدیریت پنل", body, request)

@app.get("/admin/category/new", response_class=HTMLResponse)
async def web_category_new_generic(request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    con = get_db(); panels = con.execute("select id,name from xui_panels where active=1 order by name").fetchall(); con.close()
    options = "".join(f"<option value='{p['id']}'>{html.escape(p['name'])}</option>" for p in panels)
    body = f"""<div class='card'><h2>افزودن دسته و انتخاب Inbound</h2><p class='muted'>این بخش زیرساختی است؛ محصول از بخش «ساخت و مدیریت Config» ساخته می‌شود.</p><form method='post' class='form-grid'><div class='field'><label>نام دسته‌بندی</label><input name='name' required></div><div class='field'><label>پنل فعال</label><select name='panel_id' required>{options}</select></div><div class='field'><label>Inbound IDها</label><input name='inbound_ids' required placeholder='مثلاً 1,2'></div><div class='form-actions'><button class='btn'>ذخیره دسته‌بندی</button><a href='/admin?section=panels' class='btn secondary'>انصراف</a></div></form></div>"""
    return web_render("panels", "افزودن دسته‌بندی", body, request)

@app.post("/admin/category/new")
async def web_category_new_generic_save(request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    form = await request.form(); name = str(form.get("name") or "").strip()
    try: panel_id = int(form.get("panel_id")); inbound_ids = [int(x) for x in str(form.get("inbound_ids") or "").split(",") if x.strip()]
    except (TypeError, ValueError): panel_id, inbound_ids = 0, []
    if create_category(name, panel_id, inbound_ids) is None: return web_render("panels", "افزودن دسته‌بندی", "<div class='card'>داده‌ها معتبر نیستند؛ پنل فعال و حداقل یک inbound لازم است.</div>", request)
    return RedirectResponse("/admin?section=panels", status_code=303)

@app.get("/admin/panel/{panel_id}/category/new", response_class=HTMLResponse)
async def web_category_new(panel_id: int, request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    con = get_db(); panel = con.execute("select id,name from xui_panels where id=? and active=1", (panel_id,)).fetchone(); con.close()
    if not panel: return web_render("panels", "پنل پیدا نشد", "<div class='card'>پنل فعال وجود ندارد.</div>", request)
    body = """<div class='card'><h2>افزودن دسته‌بندی و انتخاب inbound</h2><p class='muted'>نام دسته را وارد کن؛ inboundهای واقعی پنل از دکمه دریافت می‌شوند.</p><form method='post' class='form-grid'><div class='field'><label>نام دسته‌بندی</label><input name='name' required placeholder='مثلاً VIP ایران'></div><div class='field'><label>Inboundهای فعال پنل</label><div id='inbounds' class='muted'>برای دریافت inbound روی دکمه بزن.</div><button type='button' class='btn secondary' id='load-inbounds'>دریافت inboundهای پنل</button></div><input type='hidden' name='inbound_ids' id='inbound_ids'><div class='form-actions'><button class='btn'>ذخیره دسته‌بندی</button><a href='/admin/panel/%s' class='btn secondary'>انصراف</a></div></form></div><script>(function(){var btn=document.getElementById('load-inbounds'),box=document.getElementById('inbounds'),hidden=document.getElementById('inbound_ids');btn.onclick=async function(){btn.disabled=true;try{var r=await fetch('/admin/panel/%s/inbounds');var d=await r.json();if(!d.ok){box.textContent=d.message;return}box.innerHTML=d.items.map(function(x){return '<label style="display:block;margin:8px 0"><input type="checkbox" value="'+x.id+'"> '+x.id+' | '+x.remark+' | '+x.protocol+':'+x.port+'</label>'}).join('');box.querySelectorAll('input').forEach(function(i){i.onchange=function(){hidden.value=Array.from(box.querySelectorAll('input:checked')).map(function(x){return x.value}).join(',')}})}finally{btn.disabled=false}}})();</script>""" % (panel_id, panel_id)
    return web_render("panels", "افزودن دسته‌بندی", body, request)

@app.get("/admin/panel/{panel_id}/inbounds")
async def web_panel_inbounds(panel_id: int, request: Request):
    if not web_guard(request): return {"ok": False, "message": "احراز هویت لازم است."}
    panel = get_xui_panel(panel_id)
    if not panel: return {"ok": False, "message": "پنل پیدا نشد."}
    try:
        items = await XUIClient(panel).list_inbounds()
    except XUIError:
        return {"ok": False, "message": "دریافت inboundهای پنل ناموفق بود."}
    return {"ok": True, "items": items}

@app.post("/admin/panel/{panel_id}/category/new")
async def web_category_create(panel_id: int, request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    form = await request.form(); name = str(form.get("name") or "").strip()
    try: inbound_ids = [int(x) for x in str(form.get("inbound_ids") or "").split(",") if x.strip()]
    except ValueError: inbound_ids = []
    if create_category(name, panel_id, inbound_ids) is None:
        return web_render("panels", "افزودن دسته‌بندی", "<div class='card'>نام، پنل فعال و حداقل یک inbound معتبر الزامی است.</div>", request)
    return RedirectResponse(f"/admin/panel/{panel_id}", status_code=303)

@app.get("/admin/category/{category_id}/edit", response_class=HTMLResponse)
async def web_category_edit(category_id: int, request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    category = get_category_with_panel(category_id)
    if not category: return web_render("panels", "دسته پیدا نشد", "<div class='card'>دسته فعال پیدا نشد.</div>", request)
    ids = ",".join(map(str, category_inbound_ids(category)))
    body = """<div class='card'><h2>ویرایش دسته‌بندی</h2><form method='post' class='form-grid'><div class='field'><label>نام دسته‌بندی</label><input name='name' value='%s' required></div><div class='field'><label>Inbound IDها</label><input name='inbound_ids' value='%s' required><div class='hint'>چند شناسه را با کاما جدا کن؛ برای انتخاب دقیق از صفحه افزودن استفاده کن.</div></div><div class='form-actions'><button class='btn'>ذخیره</button><a href='/admin/panel/%s' class='btn secondary'>انصراف</a></div></form></div>""" % (html.escape(category['name'], quote=True), ids, category['panel_id'])
    return web_render("panels", "ویرایش دسته‌بندی", body, request)

@app.post("/admin/category/{category_id}/edit")
async def web_category_edit_save(category_id: int, request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    category = get_category_with_panel(category_id)
    if not category: return RedirectResponse("/admin?section=panels", status_code=303)
    form = await request.form(); name = str(form.get("name") or "").strip()
    try: inbound_ids = sorted({int(x) for x in str(form.get("inbound_ids") or "").split(",") if x.strip()})
    except ValueError: inbound_ids = []
    if not name or not inbound_ids: return web_render("panels", "ویرایش دسته‌بندی", "<div class='card'>نام و حداقل یک inbound معتبر الزامی است.</div>", request)
    con = get_db(); con.execute("update categories set name=?, inbound_ids=? where id=?", (name, json.dumps(inbound_ids), category_id)); con.commit(); con.close()
    return RedirectResponse(f"/admin/panel/{category['panel_id']}", status_code=303)

@app.post("/admin/panel/{panel_id}/delete")
async def web_panel_delete_route(panel_id: int, request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    con = get_db()
    panel = con.execute("select id from xui_panels where id=?", (panel_id,)).fetchone()
    if panel:
        con.execute("update products set active=0, category_id=NULL where category_id in (select id from categories where panel_id=?)", (panel_id,))
        con.execute("delete from categories where panel_id=?", (panel_id,))
        con.execute("delete from xui_panels where id=?", (panel_id,))
        con.commit()
    con.close()
    return RedirectResponse("/admin?section=panels", status_code=303)


@app.post("/admin/category/{category_id}/delete")
async def web_category_delete(category_id: int, request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    deleted, _ = delete_category(category_id)
    return RedirectResponse("/admin?section=panels", status_code=303)

@app.post("/admin/panel/{panel_id}/test")
async def web_panel_test(panel_id: int, request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    panel = get_xui_panel(panel_id)
    message="پنل پیدا نشد."
    if panel:
        try:
            result=await XUIClient(panel).list_inbounds(); message="اتصال موفق است؛ inboundها دریافت شدند." if result is not None else "پاسخ معتبری از پنل دریافت نشد."
        except XUIError:
            message="اتصال ناموفق بود. جزئیات حساس نمایش داده نمی‌شود."
    return web_render("panels","تست اتصال",f"<div class='card'>{message}</div>",request)

@app.post("/admin/home-layout")
async def web_home_layout_save(request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    form = await request.form()
    raw_rows = str(form.get("rows") or "")
    parsed_rows = []
    if raw_rows:
        for raw_row in raw_rows.split("|"):
            keys = [key for key in raw_row.split(",") if key in HOME_BUTTONS and key not in {item for row in parsed_rows for item in row}]
            if keys: parsed_rows.append(keys)
    if not parsed_rows:
        order = [key for key in str(form.get("order") or "").split(",") if key in HOME_BUTTONS]
        order += [key for key in HOME_BUTTONS if key not in order]
        parsed_rows = home_layout_rows({"order": order, "columns": form.get("columns") or 2})
    used = {key for row in parsed_rows for key in row}
    parsed_rows += [[key] for key in HOME_BUTTONS if key not in used]
    order = [key for row in parsed_rows for key in row]
    try: columns = max(1, min(int(form.get("columns") or 2), 3))
    except (TypeError, ValueError): columns = 2
    con = get_db()
    con.execute("INSERT INTO app_settings(key,value,updated_at) VALUES('home_layout',?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (json.dumps({"rows": parsed_rows, "order": order, "columns": columns}, ensure_ascii=False), now_text()))
    con.commit(); con.close()
    global main_keyboard
    main_keyboard = get_main_keyboard()
    return RedirectResponse("/admin?section=home", status_code=303)

@app.get("/admin/users", response_class=HTMLResponse)
async def web_users_compat(request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    return RedirectResponse("/admin?section=users", status_code=303)

@app.get("/admin/product/new", response_class=HTMLResponse)
async def web_product_new(request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    con=get_db(); categories=con.execute("select id,name,panel_id from categories where active=1 order by name").fetchall(); con.close()
    options="".join(f"<option value='{c['id']}'>{html.escape(c['name'])} (پنل {c['panel_id']})</option>" for c in categories)
    body=f"""<div class='card'><h2>افزودن محصول پنلی</h2><p class='muted'>محصول فقط به مدل inbound وصل می‌شود و موجودی دستی ندارد.</p><form method='post' class='form-grid'><div class='field'><label>نام محصول</label><input name='name' required></div><div class='field'><label>مدت (روز)</label><input name='duration_days' type='number' min='1' required></div><div class='field'><label>حجم (GB)</label><input name='volume_gb' type='number' min='0.01' step='0.01' required></div><div class='field'><label>قیمت (تومان)</label><input name='price' type='number' min='0' step='1' required></div><div class='field'><label>مدل inbound</label><select name='category_id' required><option value=''>انتخاب کن</option>{options}</select></div><div class='form-actions'><button class='btn'>ذخیره محصول</button><a href='/admin?section=products' class='btn secondary'>انصراف</a></div></form></div>"""
    return web_render("products", "افزودن محصول پنلی", body, request)

@app.post("/admin/product/new")
async def web_product_create(request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    form=await request.form()
    try:
        name=str(form.get("name") or "").strip(); days=int(form.get("duration_days")); volume=float(form.get("volume_gb")); price=float(form.get("price")); category_id=int(form.get("category_id"))
        category=get_category_with_panel(category_id)
        if not name or days <= 0 or volume <= 0 or price < 0 or category is None or not category_inbound_ids(category): raise ValueError
    except (TypeError, ValueError):
        return web_render("products", "افزودن محصول پنلی", "<div class='card'>اطلاعات واردشده معتبر نیست یا مدل inbound انتخاب‌شده فعال نیست.</div>", request)
    if create_product(name, days, volume, price, category_id) is None:
        return web_render("products", "افزودن محصول پنلی", "<div class='card'>محصولی با این نام قبلاً ثبت شده است.</div>", request)
    return RedirectResponse("/admin?section=products", status_code=303)

@app.get("/admin/product/{product_id}/edit", response_class=HTMLResponse)
async def web_product_edit(product_id: int, request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    con = get_db()
    product = con.execute("""select p.*, c.name as category_name from products p left join categories c on c.id=p.category_id where p.id=?""", (product_id,)).fetchone()
    categories = con.execute("select id,name,panel_id from categories where active=1 order by name").fetchall()
    con.close()
    if not product:
        return web_render("products", "ویرایش Config", "<div class='card'>محصول پیدا نشد.</div>", request)
    options = "".join(f"<option value='{c['id']}' {'selected' if c['id'] == product['category_id'] else ''}>{html.escape(c['name'])} (پنل {c['panel_id']})</option>" for c in categories)
    body = f"""<div class='card'><h2>ویرایش Config</h2><form method='post' class='form-grid'><div class='field'><label>نام محصول</label><input name='name' value='{html.escape(str(product['name']), quote=True)}' required></div><div class='field'><label>مدت (روز)</label><input name='duration_days' type='number' min='1' value='{product['duration_days']}' required></div><div class='field'><label>حجم (GB)</label><input name='volume_gb' type='number' min='0.01' step='0.01' value='{product['volume_gb']}' required></div><div class='field'><label>قیمت (تومان)</label><input name='price' type='number' min='0' step='1' value='{product['price']}' required></div><div class='field'><label>مدل inbound</label><select name='category_id' required>{options}</select></div><div class='form-actions'><button class='btn'>ذخیره تغییرات</button><a href='/admin?section=products' class='btn secondary'>انصراف</a></div></form></div>"""
    return web_render("products", "ویرایش Config", body, request)


@app.post("/admin/product/{product_id}/edit")
async def web_product_edit_save(product_id: int, request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    form = await request.form()
    try:
        name = str(form.get("name") or "").strip()
        days = int(form.get("duration_days")); volume = float(form.get("volume_gb")); price = float(form.get("price")); category_id = int(form.get("category_id"))
        category = get_category_with_panel(category_id)
        if not name or days <= 0 or volume <= 0 or price < 0 or category is None or not category_inbound_ids(category): raise ValueError
    except (TypeError, ValueError):
        return web_render("products", "ویرایش Config", "<div class='card'>اطلاعات نامعتبر است یا مدل inbound فعال نیست.</div>", request)
    if not update_product(product_id, name, days, volume, price, category_id):
        return web_render("products", "ویرایش Config", "<div class='card'>ویرایش انجام نشد؛ نام تکراری یا محصول غیرفعال است.</div>", request)
    return RedirectResponse("/admin?section=products", status_code=303)


@app.get("/admin/test", response_class=HTMLResponse)
async def web_test_settings(request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    con=get_db(); categories=con.execute("select id,name,panel_id from categories where active=1 order by name").fetchall(); con.close(); setting=get_trial_settings()
    options="".join(f"<option value='{c['id']}' {'selected' if setting and setting['category_id']==c['id'] else ''}>{html.escape(c['name'])} (پنل {c['panel_id']})</option>" for c in categories)
    current=f"{setting['duration_days']} روز / {setting['volume_gb']} GB" if setting else "تنظیم نشده"
    body=f"""<div class='card'><h2>تنظیم سرویس تست پنلی</h2><p class='muted'>وضعیت فعلی: {current}</p><form method='post' class='form-grid'><div class='field'><label>مدل inbound</label><select name='category_id' required><option value=''>انتخاب کن</option>{options}</select></div><div class='field'><label>مدت تست (روز)</label><input name='duration_days' type='number' min='1' value='{setting['duration_days'] if setting else 1}' required></div><div class='field'><label>حجم تست (GB)</label><input name='volume_gb' type='number' min='0.01' step='0.01' value='{setting['volume_gb'] if setting else 1}' required></div><div class='form-actions'><button class='btn'>ذخیره تنظیمات تست</button><a href='/admin?section=products' class='btn secondary'>انصراف</a></div></form></div>"""
    return web_render("products", "تنظیم سرویس تست", body, request)

@app.post("/admin/test")
async def web_test_settings_save(request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    form=await request.form()
    try:
        category_id=int(form.get("category_id")); days=int(form.get("duration_days")); volume=float(form.get("volume_gb")); category=get_category_with_panel(category_id)
        if days <= 0 or volume <= 0 or category is None or not category_inbound_ids(category): raise ValueError
    except (TypeError, ValueError):
        return web_render("products", "تنظیم سرویس تست", "<div class='card'>تنظیمات تست معتبر نیست.</div>", request)
    save_trial_settings(category_id, days, volume)
    return RedirectResponse("/admin?section=products", status_code=303)

@app.get("/admin/user/{telegram_id}", response_class=HTMLResponse)
async def web_user_detail(telegram_id: int, request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    con=get_db(); user=con.execute("select * from users where telegram_id=?", (telegram_id,)).fetchone(); orders=con.execute("select o.id,o.status,o.amount,o.created_at,p.name from orders o left join products p on p.id=o.product_id where o.telegram_id=? order by o.id desc limit 20", (telegram_id,)).fetchall(); con.close()
    if not user: return web_render("users", "کاربر پیدا نشد", "<div class='card'>کاربر وجود ندارد.</div>", request)
    body=Template("""<div class='card'><h2>{{u['first_name'] or 'کاربر'}}</h2><p class='muted'>Telegram ID: {{u['telegram_id']}} · Username: {{u['username'] or '—'}}</p><p style='font-size:14px;margin:0 0 18px'>موجودی فعلی: <b>{{u['balance']}}</b> تومان</p><form method='post' action='/admin/user/{{u['telegram_id']}}/balance' class='form-grid' style='max-width:360px'><div class='field'><label>مقدار تغییر موجودی (مثبت یا منفی)</label><input name='amount' type='number' step='1' required placeholder='مثلاً 50000 یا -20000'></div><button class='btn'>ثبت تغییر موجودی</button></form></div><div class='card'><h2>آخرین سفارش‌ها</h2>{% if orders %}<div class='table-wrap'><table><tr><th>شناسه</th><th>محصول</th><th>مبلغ</th><th>وضعیت</th><th>تاریخ</th></tr>{% for o in orders %}<tr><td>{{o['id']}}</td><td>{{o['name'] or '—'}}</td><td>{{o['amount']}}</td><td>{{o['status']}}</td><td>{{o['created_at']}}</td></tr>{% endfor %}</table></div>{% else %}<div class='empty'><div class='ic'>📦</div>سفارشی ثبت نشده است.</div>{% endif %}</div>""").render(u=user, orders=orders)
    return web_render("users", "جزئیات کاربر", body, request)

@app.post("/admin/user/{telegram_id}/balance")
async def web_user_balance(telegram_id: int, request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    try: amount=float((await request.form()).get("amount"))
    except (TypeError, ValueError): return web_render("users", "تغییر موجودی", "<div class='card'>مقدار نامعتبر است.</div>", request)
    con=get_db(); cur=con.execute("update users set balance=balance+? where telegram_id=?", (amount, telegram_id)); con.commit(); con.close()
    if cur.rowcount == 0: return web_render("users", "تغییر موجودی", "<div class='card'>کاربر پیدا نشد.</div>", request)
    return RedirectResponse(f"/admin/user/{telegram_id}", status_code=303)

async def web_panel_status(request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    con = get_db()
    panels = con.execute("select id,name,base_url,active,subscription_url,api_token from xui_panels order by id desc").fetchall()
    con.close()
    rows = []
    for panel in panels:
        try:
            snapshot = await fetch_panel_status(dict(panel))
        except Exception:
            snapshot = {"reachable": False, "latency_ms": None, "api": "offline", "server_status": None, "inbounds": [], "error": "بررسی وضعیت پنل با خطای داخلی مواجه شد."}
        rows.append({"panel": panel, "status": snapshot})
    body = Template("""<div class='card'><h2>وضعیت واقعی پنل‌ها</h2><p class='muted'>برای هر پنل درخواست احراز هویت‌شده به API ارسال می‌شود. نتیجه شامل سلامت API، Ping، CPU، RAM، Disk، Xray و inboundهاست.</p></div><div class='card'><div class='table-wrap'><table><tr><th>پنل</th><th>وضعیت API</th><th>Ping</th><th>سرور</th><th>Xray</th><th>Inbound</th><th>جزئیات</th></tr>{% for item in rows %}{% set s=item['status'] %}{% set server=s['server_status'] or {} %}{% set xray=server.get('xray') or {} %}<tr><td>{{item['panel']['name']}}<br><small>{{item['panel']['base_url']}}</small></td><td>{% if s['api']=='online' %}<span class='badge'>آنلاین</span>{% else %}<span class='badge off'>آفلاین</span>{% endif %}</td><td>{{s['latency_ms'] or '—'}}{% if s['latency_ms'] %} ms{% endif %}</td><td>CPU: {{server.get('cpu','—')}}<br>RAM: {{server.get('mem',{}).get('current','—')}} / {{server.get('mem',{}).get('total','—')}}<br>Disk: {{server.get('disk',{}).get('current','—')}} / {{server.get('disk',{}).get('total','—')}}</td><td>{{xray.get('state','—')}}<br>{{xray.get('version','—')}}</td><td>{{s['inbounds']|length}}</td><td>{{s['error'] or 'تأیید شد'}}</td></tr>{% else %}<tr><td colspan='7'>پنلی ثبت نشده است.</td></tr>{% endfor %}</table></div></div>""").render(rows=rows)
    return web_render("panel-status", "وضعیت واقعی پنل‌ها", body, request)


@app.get("/admin/panel-status", response_class=HTMLResponse)
async def web_panel_status_route(request: Request):
    return await web_panel_status(request)


@app.post("/admin/product/{product_id}/delete")
async def web_product_delete(product_id: int, request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    con=get_db()
    cur=con.execute("UPDATE products SET active=0, category_id=NULL WHERE id=?", (product_id,))
    con.commit()
    con.close()
    return RedirectResponse("/admin?section=products", status_code=303)

@app.post("/admin/product/{product_id}/disable")
async def web_product_disable(product_id: int, request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    con=get_db(); con.execute("update products set active=0 where id=?",(product_id,)); con.commit(); con.close(); return RedirectResponse("/admin?section=products",status_code=303)
@app.post("/admin/product/{product_id}/enable")
async def web_product_enable(product_id: int, request: Request):
    if not web_guard(request): return RedirectResponse("/admin", status_code=303)
    con=get_db(); con.execute("update products set active=1 where id=? and category_id in (select c.id from categories c join xui_panels p on p.id=c.panel_id where c.active=1 and p.active=1)", (product_id,)); con.commit(); con.close(); return RedirectResponse("/admin?section=products",status_code=303)

@app.get("/admin/logout")
async def web_logout(request: Request):
    token=request.cookies.get(WEB_SESSION_COOKIE); WEB_SESSIONS.pop(token, None)
    response=RedirectResponse("/admin",status_code=303); response.delete_cookie(WEB_SESSION_COOKIE); return response

DATABASE_FILE = Path(os.getenv("DATABASE_FILE", str(BASE_DIR / "bot.db")))
if not DATABASE_FILE.is_absolute():
    DATABASE_FILE = BASE_DIR / DATABASE_FILE
WEB_ONLY_MODE = os.getenv("WEB_ONLY", "0") == "1"
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# The Web Panel is intentionally able to start without Telegram credentials.
# The Telegram service still requires a valid BOT_TOKEN.
if not BOT_TOKEN and not WEB_ONLY_MODE:
    raise RuntimeError(
        "مقدار BOT_TOKEN داخل فایل .env تنظیم نشده است."
    )


ADMIN_IDS = {
    int(item.strip())
    for item in os.getenv("ADMIN_IDS", "").split(",")
    if item.strip().isdigit()
}


CARD_NUMBER = os.getenv(
    "CARD_NUMBER",
    "شماره کارت تنظیم نشده",
).strip()


CARD_OWNER = os.getenv(
    "CARD_OWNER",
    "نام صاحب کارت تنظیم نشده",
).strip()


SUPPORT_USERNAME = os.getenv(
    "SUPPORT_USERNAME",
    "",
).strip()

if SUPPORT_USERNAME and not SUPPORT_USERNAME.startswith("@"):
    SUPPORT_USERNAME = "@" + SUPPORT_USERNAME


try:
    AUTO_APPROVE_MINUTES = int(
        os.getenv("AUTO_APPROVE_MINUTES", "30")
    )
except ValueError:
    AUTO_APPROVE_MINUTES = 30


if AUTO_APPROVE_MINUTES < 1:
    AUTO_APPROVE_MINUTES = 30


REQUIRED_CHANNEL = os.getenv(
    "REQUIRED_CHANNEL",
    "",
).strip()

if REQUIRED_CHANNEL and not REQUIRED_CHANNEL.startswith("@"):
    REQUIRED_CHANNEL = "@" + REQUIRED_CHANNEL


try:
    BACKUP_INTERVAL_HOURS = int(
        os.getenv("BACKUP_INTERVAL_HOURS", "6")
    )
except ValueError:
    BACKUP_INTERVAL_HOURS = 6

if BACKUP_INTERVAL_HOURS < 1:
    BACKUP_INTERVAL_HOURS = 6


# ساختار سیستم‌عامل‌ها و کلاینت‌های آموزش اتصال.
# برای افزودن/حذف سیستم‌عامل یا کلاینت، همین دیکشنری را ویرایش کن.
TUTORIAL_STRUCTURE = {
    "android": {
        "label": "🤖 اندروید",
        "clients": {
            "v2rayng": "v2rayNG",
            "v2box": "v2Box",
            "hiddify": "Hiddify",
        },
    },
    "ios": {
        "label": "🍏 آی‌او‌اس",
        "clients": {
            "v2box": "v2Box",
        },
    },
    "windows": {
        "label": "🖥 ویندوز",
        "clients": {
            "v2rayn": "v2rayN",
            "hiddify": "Hiddify",
        },
    },
}


def get_telegram_proxy() -> str | None:
    proxy = os.getenv("TELEGRAM_PROXY", "").strip()
    return proxy or None


async def delete_webhook_with_retry(bot_instance, attempts: int = 3, base_delay: float = 2.0) -> bool:
    for attempt in range(max(1, attempts)):
        try:
            await bot_instance.delete_webhook(drop_pending_updates=False)
            return True
        except Exception as error:
            if attempt + 1 >= max(1, attempts):
                print("Telegram connection unavailable; polling will retry automatically.")
                return False
            if base_delay > 0:
                await asyncio.sleep(base_delay * (2 ** attempt))
    return False


telegram_proxy = get_telegram_proxy()
try:
    telegram_session = AiohttpSession(proxy=telegram_proxy) if telegram_proxy else None
except (RuntimeError, ValueError) as error:
    raise RuntimeError("TELEGRAM_PROXY تنظیم شده اما قابل استفاده نیست؛ آدرس Proxy را بررسی کن.") from error

bot = None
if BOT_TOKEN and not WEB_ONLY_MODE:
    bot = Bot(token=BOT_TOKEN, session=telegram_session)
dp = Dispatcher(storage=MemoryStorage())


# =========================================================
# ابزارها
# =========================================================

def now_text() -> str:
    return datetime.now().isoformat(
        timespec="seconds"
    )


def parse_datetime(value: str):
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def parse_telegram_post_link(link: str):
    """
    یک لینک پست کانال تلگرام مثل:
        https://t.me/mychannel/123
        https://t.me/mychannel/123?single
        t.me/c/1234567890/123  (کانال خصوصی)
    را به (chat_id, message_id) تبدیل می‌کند.
    در صورت نامعتبر بودن لینک، None برمی‌گرداند.
    """

    link = link.strip()

    if not link:
        return None

    link = link.split("?")[0].rstrip("/")

    for prefix in (
        "https://t.me/",
        "http://t.me/",
        "https://telegram.me/",
        "http://telegram.me/",
        "t.me/",
        "telegram.me/",
    ):
        if link.startswith(prefix):
            link = link[len(prefix):]
            break
    else:
        return None

    parts = [part for part in link.split("/") if part]

    if len(parts) < 2:
        return None

    # کانال خصوصی: t.me/c/<internal_id>/<message_id>
    if parts[0] == "c" and len(parts) >= 3:
        internal_id = parts[1]
        message_id_str = parts[2]

        if not internal_id.isdigit() or not message_id_str.isdigit():
            return None

        chat_id = "-100" + internal_id
        return chat_id, int(message_id_str)

    # کانال عمومی: t.me/<username>/<message_id>
    username, message_id_str = parts[0], parts[1]

    if not message_id_str.isdigit():
        return None

    chat_id = "@" + username
    return chat_id, int(message_id_str)


# =========================================================
# اتصال به پنل 3x-ui
# =========================================================

class XUIError(RuntimeError):
    """خطای قابل‌نمایش برای ارتباط با پنل 3x-ui."""


def normalize_xui_base_url(value: str) -> str:
    value = (value or "").strip().rstrip("/")
    for suffix in ("/panel/api", "/panel"):
        if value.endswith(suffix):
            value = value[: -len(suffix)].rstrip("/")
    return value


def qr_png_bytes(value: str) -> bytes:
    image = qrcode.make(value)
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def client_name_exists(name: str) -> bool:
    connection = get_db()
    row = connection.execute(
        "SELECT 1 FROM orders WHERE xui_email = ? LIMIT 1", (name,)
    ).fetchone()
    connection.close()
    return row is not None


def make_client_name(telegram_id: int, order_id: int | str, prefix: str = "user", username: str | None = None) -> str:
    """Return a short client name based on the Telegram username."""
    raw_username = username or str(telegram_id)
    return re.sub(r"[^a-zA-Z0-9_-]", "", raw_username.lstrip("@"))[:32] or f"user{telegram_id}"


def make_client_name_for_user(telegram_id: int, order_id: int | str, prefix: str = "user") -> str:
    user = get_user(telegram_id)
    username = user["username"] if user is not None and user["username"] else None
    base = make_client_name(telegram_id, order_id, username=username)
    if not client_name_exists(base):
        return base
    suffix = 2
    while client_name_exists(f"{base}_{suffix}"):
        suffix += 1
    return f"{base}_{suffix}"


def build_xui_client_payload(email: str, total_gb: float, duration_days: int,
                             telegram_id: int | None, inbound_ids: list[int],
                             now_ms: int | None = None,
                             start_after_first_use: bool = False,
                             sub_id: str | None = None) -> dict:
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    duration_ms = max(0, int(duration_days)) * 86_400_000
    if duration_ms == 0:
        expiry_time = 0
    elif start_after_first_use:
        # 3x-ui interprets a negative expiryTime as a duration that starts
        # when the client makes its first connection.
        expiry_time = -duration_ms
    else:
        expiry_time = now_ms + duration_ms
    return {
        "client": {
            "email": email,
            "subId": sub_id or email,
            "totalGB": int(max(0, total_gb) * 1024**3),
            "expiryTime": expiry_time,
            "tgId": telegram_id,
            "limitIp": 0,
            "limitHwid": 0,
            "enable": True,
        },
        "inboundIds": inbound_ids,
    }


def parse_xui_links_response(data: dict) -> list[str]:
    if not isinstance(data, dict) or not data.get("success"):
        return []
    obj = data.get("obj")
    if isinstance(obj, list):
        return [str(item) for item in obj if item]
    if isinstance(obj, dict):
        links = obj.get("links") or obj.get("obj") or []
        if isinstance(links, list):
            return [str(item) for item in links if item]
    return []


def parse_xui_sub_id(data: dict) -> str | None:
    """Extract subId from all common 3x-ui client-add response shapes."""
    if not isinstance(data, dict) or not data.get("success"):
        return None
    candidates = []

    def collect(value):
        if isinstance(value, dict):
            for key in ("subId", "sub_id", "subID", "subscriptionId", "subscription_id"):
                if value.get(key):
                    candidates.append(value[key])
            for child in value.values():
                if isinstance(child, (dict, list)):
                    collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(data.get("obj"))
    for value in candidates:
        if value:
            return str(value)
    return None


def new_sub_id() -> str:
    """Fallback identifier used by 3x-ui builds that do not return subId."""
    return uuid.uuid4().hex


def build_subscription_url(panel, sub_id: str | None) -> str | None:
    """Build the public subscription URL from a sample URL or template."""
    if not sub_id:
        return None
    if hasattr(panel, "get"):
        template = (
            panel.get("subscription_url")
            or panel.get("panel_subscription_url")
            or panel.get("subscription_template")
            or ""
        )
    else:
        try:
            template = (
                panel["subscription_url"]
                or panel["panel_subscription_url"]
                or panel["subscription_template"]
                or ""
            )
        except (KeyError, IndexError, TypeError):
            template = ""
    template = str(template).strip()
    if not template:
        return None
    token = quote(str(sub_id), safe="")
    if "{sub_id}" in template:
        return template.replace("{sub_id}", token)
    if "{subId}" in template:
        return template.replace("{subId}", token)
    parts = urlsplit(template)
    path = parts.path.rstrip("/")
    if "/sub/" in path:
        path = path[:path.rfind("/sub/") + 5] + token
    elif path.endswith("/sub"):
        path += "/" + token
    else:
        path += "/sub/" + token
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def _format_bytes(value: float) -> str:
    value = max(0.0, float(value))
    units = ("B", "GB", "TB")
    amount = value
    unit = units[0]
    if value >= 1024**4:
        amount, unit = value / 1024**4, "TB"
    elif value >= 1024**3:
        amount, unit = value / 1024**3, "GB"
    elif value >= 1024**2:
        amount, unit = value / 1024**2, "MB"
    return f"{amount:.2f} {unit}"


def format_server_status(status: dict) -> str:
    status = status or {}
    mem = status.get("mem") or {}
    disk = status.get("disk") or {}
    xray = status.get("xray") or {}
    return (
        f"🖥 CPU: {float(status.get('cpu') or 0):.1f}%\n"
        f"🧠 RAM: {_format_bytes(mem.get('current', 0))} / {_format_bytes(mem.get('total', 0))}\n"
        f"💽 دیسک: {_format_bytes(disk.get('current', 0))} / {_format_bytes(disk.get('total', 0))}\n"
        f"🚀 Xray: {xray.get('state') or 'نامشخص'}"
        f" ({xray.get('version') or '—'})\n"
        f"🔌 اتصال TCP: {status.get('tcpCount', '—')}"
    )


def qr_png_bytes(value: str) -> bytes:
    image = qrcode.make(value)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def parse_xui_inbounds(data: dict) -> list[dict]:
    if not isinstance(data, dict) or not data.get("success"):
        return []
    items = data.get("obj") or data.get("data") or []
    if isinstance(items, dict):
        items = items.get("inbounds") or items.get("items") or []
    result = []
    for item in items if isinstance(items, list) else []:
        try:
            inbound_id = int(item.get("id"))
        except (TypeError, ValueError, AttributeError):
            continue
        result.append({
            "id": inbound_id,
            "remark": str(item.get("remark") or item.get("tag") or "بدون نام"),
            "protocol": str(item.get("protocol") or "—"),
            "port": item.get("port") or "—",
        })
    return result


def _bytes_to_gb(value: float) -> float:
    return max(0.0, float(value)) / 1024**3


def format_traffic_status(traffic: dict, now_ms: int | None = None) -> str:
    traffic = traffic or {}
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    up = float(traffic.get("up") or 0)
    down = float(traffic.get("down") or 0)
    total = float(traffic.get("total") or 0)
    used = up + down
    volume_text = "نامحدود" if total == 0 else (
        f"{_bytes_to_gb(max(0.0, total - used)):.2f} GB باقی‌مانده از "
        f"{_bytes_to_gb(total):.2f} GB"
    )
    expiry = int(traffic.get("expiryTime") or 0)
    if expiry == 0:
        expiry_text = "بدون انقضا"
    else:
        seconds = max(0, (expiry - now_ms) // 1000)
        days, remainder = divmod(seconds, 86_400)
        expiry_text = f"{days} روز و {remainder // 3_600} ساعت باقی‌مانده"
    return (
        f"📊 حجم مصرف‌شده: {_bytes_to_gb(used):.2f} GB\n"
        f"📦 حجم باقی‌مانده: {volume_text}\n"
        f"⏳ زمان: {expiry_text}\n"
        f"🔌 وضعیت: {'فعال' if traffic.get('enable', True) else 'غیرفعال'}"
    )




def panel_status_snapshot(panel) -> dict:
    """Return safe network/API health data; never include the API token."""
    parsed = urlsplit(normalize_xui_base_url(panel["base_url"]))
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    result = {"reachable": False, "latency_ms": None, "api": "نامشخص", "server_status": None, "inbounds": 0, "error": None}
    if not host:
        result["error"] = "آدرس پنل معتبر نیست."
        return result
    started = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=4):
            result["reachable"] = True
            result["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
    except (OSError, ValueError) as error:
        result["error"] = "سرور پاسخ نداد."
        return result
    return result


def panel_status_text(panel, status: dict) -> str:
    if status.get("api") != "online":
        return "❌ آفلاین — درخواست API ناموفق بود"
    latency = status.get("latency_ms")
    return f"✅ آنلاین — Ping: {latency} ms | API: آنلاین"


async def fetch_panel_status(panel, transport=None) -> dict:
    """Perform real authenticated API checks and return safe public details."""
    result = {"reachable": False, "latency_ms": None, "api": "offline", "server_status": None, "inbounds": [], "error": None}
    client = XUIClient(panel, transport=transport)
    started = time.perf_counter()
    try:
        server_status = await client.get_server_status()
        result["server_status"] = server_status
        result["api"] = "online"
        result["reachable"] = True
        result["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
    except XUIError as error:
        result["error"] = "دسترسی API پنل ناموفق بود."
        return result
    try:
        result["inbounds"] = await client.list_inbounds()
    except XUIError:
        result["error"] = "API فعال است اما دریافت inboundها ناموفق بود."
    return result


class XUIClient:
    def __init__(self, panel, transport=None):
        self.base_url = normalize_xui_base_url(panel["base_url"])
        self.token = panel["api_token"]
        self.transport = transport
        self.timeout = httpx.Timeout(15.0, connect=8.0)

    def _url(self, path: str) -> str:
        return f"{self.base_url}/panel/api/{path.lstrip('/')}"

    async def _request(self, method: str, path: str, **kwargs):
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.token}"
        headers.setdefault("Accept", "application/json")
        try:
            async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
                response = await client.request(method, self._url(path), headers=headers, **kwargs)
        except httpx.HTTPError as error:
            raise XUIError("اتصال به پنل برقرار نشد.") from error
        try:
            data = response.json()
        except ValueError as error:
            raise XUIError(f"پاسخ پنل معتبر نیست (HTTP {response.status_code}).") from error
        if response.status_code >= 400 or not data.get("success", False):
            message = data.get("msg") or data.get("message") or f"HTTP {response.status_code}"
            raise XUIError(f"پنل خطا داد: {message}")
        return data

    async def list_inbounds(self) -> list[dict]:
        try:
            data = await self._request("GET", "inbounds/options")
        except XUIError as error:
            if "HTTP 404" not in str(error):
                raise
            data = await self._request("GET", "inbounds/list")
        result = parse_xui_inbounds(data)
        if not result:
            raise XUIError("پنل هیچ inbound قابل استفاده‌ای برنگرداند.")
        return result

    async def add_client(self, email: str, total_gb: float, duration_days: int,
                         telegram_id: int | None, inbound_ids: list[int],
                         start_after_first_use: bool = False,
                         sub_id: str | None = None) -> dict:
        return await self._request(
            "POST", "clients/add",
            json=build_xui_client_payload(
                email, total_gb, duration_days, telegram_id, inbound_ids,
                start_after_first_use=start_after_first_use,
                sub_id=sub_id,
            ),
        )

    async def get_links(self, email: str) -> list[str]:
        data = await self._request("GET", f"clients/links/{quote(email, safe='')}")
        links = parse_xui_links_response(data)
        if not links:
            raise XUIError("پنل برای این اشتراک لینک اتصال برنگرداند.")
        return links

    async def get_sub_links(self, sub_id: str) -> list[str]:
        data = await self._request("GET", f"clients/subLinks/{quote(sub_id, safe='')}")
        links = parse_xui_links_response(data)
        if not links:
            raise XUIError("پنل برای این subId لینک اتصال برنگرداند.")
        return links

    async def get_client(self, email: str) -> dict:
        data = await self._request("GET", f"clients/get/{quote(email, safe='')}")
        if not isinstance(data.get("obj"), dict):
            raise XUIError("اطلاعات کلاینت از پنل دریافت نشد.")
        return data["obj"]

    async def get_client_sub_id(self, email: str) -> str | None:
        """Find subId from the client endpoint, including nested response shapes."""
        data = await self._request("GET", f"clients/get/{quote(email, safe='')}")
        return parse_xui_sub_id(data)

    async def get_server_status(self) -> dict:
        data = await self._request("GET", "server/status")
        if not isinstance(data.get("obj"), dict):
            raise XUIError("وضعیت سرور از پنل دریافت نشد.")
        return data["obj"]

    async def get_traffic(self, email: str) -> dict:
        data = await self._request("GET", f"clients/traffic/{quote(email, safe='')}")
        traffic = data.get("obj")
        if not isinstance(traffic, dict):
            raise XUIError("اطلاعات مصرف از پنل دریافت نشد.")
        return traffic

    async def delete_client(self, email: str):
        return await self._request("POST", f"clients/del/{quote(email, safe='')}?keepTraffic=0")


_extra_admin_ids_cache: set[int] = set()


def load_extra_admins():
    """کش ادمین‌های اضافه‌شده از دیتابیس را در حافظه بارگذاری می‌کند."""

    global _extra_admin_ids_cache

    connection = get_db()

    rows = connection.execute(
        "SELECT telegram_id FROM admins"
    ).fetchall()

    connection.close()

    _extra_admin_ids_cache = {
        row["telegram_id"] for row in rows
    }


def is_admin(user_id: int) -> bool:
    return (
        user_id in ADMIN_IDS
        or user_id in _extra_admin_ids_cache
    )


def is_super_admin(user_id: int) -> bool:
    """
    سوپرادمین یعنی همان‌هایی که از طریق ENV (ADMIN_IDS) تنظیم
    شده‌اند. فقط سوپرادمین‌ها می‌توانند ادمین اضافه/حذف کنند.
    """
    return user_id in ADMIN_IDS


def add_admin(telegram_id: int, added_by: int) -> bool:
    connection = get_db()

    try:
        connection.execute(
            """
            INSERT INTO admins (
                telegram_id,
                added_by,
                added_at
            )
            VALUES (?, ?, ?)
            """,
            (
                telegram_id,
                added_by,
                now_text(),
            ),
        )

        connection.commit()

    except sqlite3.IntegrityError:
        connection.close()
        return False

    connection.close()

    _extra_admin_ids_cache.add(telegram_id)
    return True


def remove_admin(telegram_id: int) -> bool:
    connection = get_db()

    cursor = connection.execute(
        """
        DELETE FROM admins
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )

    connection.commit()
    connection.close()

    removed = cursor.rowcount > 0

    _extra_admin_ids_cache.discard(telegram_id)
    return removed


def delete_xui_panel(panel_id: int) -> tuple[bool, str]:
    connection = get_db()
    try:
        connection.execute("BEGIN IMMEDIATE")
        panel = connection.execute("SELECT name FROM xui_panels WHERE id = ?", (panel_id,)).fetchone()
        if panel is None:
            connection.rollback()
            return False, "پنل پیدا نشد."
        linked_product_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM products
            WHERE category_id IN (SELECT id FROM categories WHERE panel_id = ?)
              AND active = 1
            """,
            (panel_id,),
        ).fetchone()[0]
        # با حذف پنل، محصولات وابسته قابل فروش نمی‌مانند؛ آن‌ها را غیرفعال
        # و از دسته‌بندی جدا می‌کنیم تا حذف بدون خطای وابستگی انجام شود.
        connection.execute(
            """
            UPDATE products
            SET active = 0, category_id = NULL
            WHERE category_id IN (SELECT id FROM categories WHERE panel_id = ?)
            """,
            (panel_id,),
        )
        connection.execute("DELETE FROM xui_panel_settings WHERE panel_id = ?", (panel_id,))
        connection.execute("DELETE FROM categories WHERE panel_id = ?", (panel_id,))
        connection.execute("DELETE FROM xui_panels WHERE id = ?", (panel_id,))
        connection.commit()
        suffix = f" {linked_product_count} محصول وابسته غیرفعال شد." if linked_product_count else ""
        return True, f"پنل «{panel['name']}» حذف شد.{suffix}"
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_all_admins():
    """
    لیست همه ادمین‌ها را برمی‌گرداند: سوپرادمین‌های ENV و
    ادمین‌های اضافه‌شده از دیتابیس، به‌همراه نوعشان.
    """

    connection = get_db()

    rows = connection.execute(
        """
        SELECT telegram_id, added_at
        FROM admins
        ORDER BY id ASC
        """
    ).fetchall()

    connection.close()

    admins = [
        {
            "telegram_id": admin_id,
            "type": "super",
            "added_at": None,
        }
        for admin_id in sorted(ADMIN_IDS)
    ]

    admins.extend(
        {
            "telegram_id": row["telegram_id"],
            "type": "extra",
            "added_at": row["added_at"],
        }
        for row in rows
    )

    return admins


async def is_channel_member(user_id: int) -> bool:
    """
    بررسی می‌کند کاربر عضو کانال اجباری است یا نه.
    اگر کانال تنظیم نشده باشد یا خطایی رخ دهد (مثلاً ربات
    ادمین کانال نباشد)، برای جلوگیری از قفل‌شدن کامل ربات،
    عبور را مجاز می‌کند و خطا را لاگ می‌کند.
    """

    if not REQUIRED_CHANNEL:
        return True

    try:
        member = await bot.get_chat_member(
            chat_id=REQUIRED_CHANNEL,
            user_id=user_id,
        )

        return member.status in (
            "member",
            "administrator",
            "creator",
        )

    except Exception as error:
        print(
            "خطا در بررسی عضویت کانال:",
            error,
        )
        return True


def join_channel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📢 عضویت در کانال",
                    url=f"https://t.me/{REQUIRED_CHANNEL.lstrip('@')}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ عضو شدم",
                    callback_data="check_join",
                )
            ],
        ]
    )


def get_db():
    global DATABASE_FILE
    DATABASE_FILE = Path(DATABASE_FILE)
    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(
        DATABASE_FILE,
        timeout=30,
    )

    connection.row_factory = sqlite3.Row
    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


def save_user(user):
    connection = get_db()

    connection.execute(
        """
        INSERT INTO users (
            telegram_id,
            username,
            first_name,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(telegram_id)
        DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            updated_at = excluded.updated_at
        """,
        (
            user.id,
            user.username,
            user.first_name,
            now_text(),
            now_text(),
        ),
    )

    connection.commit()
    connection.close()


# =========================================================
# ساخت دیتابیس
# =========================================================

def init_database():
    connection = get_db()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            balance REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    # افزودن ستون balance برای دیتابیس‌های قدیمی که این ستون را ندارند
    try:
        connection.execute(
            "ALTER TABLE users ADD COLUMN balance REAL NOT NULL DEFAULT 0"
        )
        connection.commit()
    except sqlite3.OperationalError:
        pass

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS xui_panels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            base_url TEXT NOT NULL,
            api_token TEXT NOT NULL,
            subscription_url TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
        """
    )

    # ستون‌های افزوده‌شده برای دیتابیس‌های قدیمی
    try:
        connection.execute("ALTER TABLE xui_panels ADD COLUMN subscription_url TEXT")
        connection.commit()
    except sqlite3.OperationalError:
        pass

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS xui_panel_settings (
            panel_id INTEGER PRIMARY KEY,
            subscription_template TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(panel_id) REFERENCES xui_panels(id)
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            panel_id INTEGER,
            inbound_ids TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            FOREIGN KEY(panel_id)
                REFERENCES xui_panels(id)
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            duration_days INTEGER NOT NULL,
            volume_gb REAL NOT NULL,
            price REAL NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            category_id INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY(category_id)
                REFERENCES categories(id)
        )
        """
    )

    # افزودن ستون category_id برای دیتابیس‌های قدیمی
    try:
        connection.execute(
            "ALTER TABLE products ADD COLUMN category_id INTEGER"
        )
        connection.commit()
    except sqlite3.OperationalError:
        pass

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config TEXT UNIQUE NOT NULL,
            product_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'available',
            added_at TEXT NOT NULL,
            sold_to INTEGER,
            sold_at TEXT,
            FOREIGN KEY(product_id)
                REFERENCES products(id)
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            amount REAL NOT NULL,

            status TEXT NOT NULL,

            proof_type TEXT,
            proof_file_id TEXT,
            proof_text TEXT,

            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,

            approved_at TEXT,
            approved_by INTEGER,
            rejected_at TEXT,
            rejected_by INTEGER,

            delivered_config TEXT,
            xui_email TEXT,
            subscription_url TEXT,
            sub_id TEXT,
            duration_days INTEGER,
            volume_gb REAL,

            FOREIGN KEY(product_id)
                REFERENCES products(id)
        )
        """
    )
    # اسنپ‌شات مدت/حجم در لحظه خرید روی خود سفارش ثبت می‌شود تا
    # تغییر یا حذف محصول بعدی روی سفارش‌های قدیمی اثر نگذارد.

    # افزودن ستون‌های اشتراک برای دیتابیس‌های قدیمی
    for column in ("subscription_url", "sub_id", "duration_days", "volume_gb"):
        try:
            connection.execute(f"ALTER TABLE orders ADD COLUMN {column} TEXT")
            connection.commit()
        except sqlite3.OperationalError:
            pass

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_orders_status
        ON orders(status)
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_inventory_product_status
        ON inventory(product_id, status)
        """
    )

    # ---- جداول تست رایگان (کاملاً جدا از موجودی فروش) ----

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS trial_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL DEFAULT 'available',
            added_at TEXT NOT NULL,
            given_to INTEGER,
            given_at TEXT
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_trial_inventory_status
        ON trial_inventory(status)
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS trial_claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            config TEXT NOT NULL,
            claimed_at TEXT NOT NULL
        )
        """
    )

    # ---- تراکنش‌های کیف پول ----

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS wallet_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            note TEXT,
            admin_id INTEGER,
            created_at TEXT NOT NULL
        )
        """
    )

    # ---- درخواست‌های شارژ کیف پول (کارت‌به‌کارت) ----

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS topup_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            amount REAL NOT NULL,

            status TEXT NOT NULL,

            proof_type TEXT,
            proof_file_id TEXT,
            proof_text TEXT,

            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,

            approved_at TEXT,
            approved_by INTEGER,
            rejected_at TEXT,
            rejected_by INTEGER
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_topup_status
        ON topup_requests(status)
        """
    )

    # ---- ویدیوهای آموزش اتصال (بر اساس سیستم‌عامل + کلاینت) ----

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tutorial_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            os_key TEXT NOT NULL,
            client_key TEXT NOT NULL,
            chat_id TEXT NOT NULL,
            message_id INTEGER NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(os_key, client_key)
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS trial_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            category_id INTEGER,
            duration_days INTEGER NOT NULL DEFAULT 1,
            volume_gb REAL NOT NULL DEFAULT 1,
            active INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(category_id) REFERENCES categories(id)
        )
        """
    )

    for column, definition in (
        ("xui_email", "TEXT"),
        ("category_id", "INTEGER"),
        ("status", "TEXT NOT NULL DEFAULT 'active'"),
    ):
        try:
            connection.execute(f"ALTER TABLE trial_claims ADD COLUMN {column} {definition}")
            connection.commit()
        except sqlite3.OperationalError:
            pass

    # ---- ادمین‌های افزوده‌شده از داخل ربات ----
    # ادمین‌های اصلی (سوپرادمین) همچنان از ENV (ADMIN_IDS) خوانده
    # می‌شوند و قابل حذف از این جدول نیستند.

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            added_by INTEGER,
            added_at TEXT NOT NULL
        )
        """
    )

    # محصولات قدیمیِ موجودی دستی دیگر در فروش قابل استفاده نیستند.
    # رکورد سفارش‌های قبلی حفظ می‌شود؛ فقط محصول و موجودی دستی غیرفعال/پاک می‌شوند.
    connection.execute("UPDATE products SET active = 0 WHERE category_id IS NULL")
    connection.execute("DELETE FROM inventory")

    connection.commit()
    connection.close()


# =========================================================
# وضعیت‌های ربات
# =========================================================

class AdminStates(StatesGroup):
    waiting_product_name = State()
    waiting_product_days = State()
    waiting_product_volume = State()
    waiting_product_price = State()
    waiting_product_category = State()
    waiting_product_edit_name = State()
    waiting_product_edit_days = State()
    waiting_product_edit_volume = State()
    waiting_product_edit_price = State()
    waiting_product_edit_category = State()

    waiting_stock_product_id = State()
    waiting_stock_configs = State()

    waiting_trial_configs = State()

    waiting_user_search = State()
    waiting_balance_amount = State()
    waiting_broadcast_message = State()
    waiting_tutorial_video = State()
    waiting_new_admin_id = State()
    waiting_remove_admin_id = State()
    waiting_panel_name = State()
    waiting_panel_url = State()
    waiting_panel_subscription_url = State()
    waiting_panel_subscription_update = State()
    waiting_panel_token = State()
    waiting_category_name = State()
    waiting_category_panel = State()
    waiting_category_inbounds = State()
    waiting_trial_category = State()
    waiting_trial_days = State()
    waiting_trial_volume = State()


class UserStates(StatesGroup):
    waiting_payment_proof = State()
    waiting_topup_amount = State()
    waiting_topup_proof = State()
    waiting_trial_category = State()
    waiting_subscription_traffic = State()


# =========================================================
# کیبوردها
# =========================================================

HOME_BUTTONS = {
    "trial": "🎁 تست رایگان",
    "buy": "🛒 خرید اشتراک",
    "subscriptions": "📦 اشتراک‌های من",
    "tutorial": "📚 آموزش اتصال",
    "support": "🆘 پشتیبانی",
    "account": "👤 حساب کاربری",
}
HOME_DEFAULT_LAYOUT = {"order": list(HOME_BUTTONS), "columns": 2}


def home_layout_rows(layout: dict) -> list[list[str]]:
    """Normalize a saved keyboard layout to explicit two-dimensional rows."""
    valid = set(HOME_BUTTONS)
    rows = layout.get("rows") if isinstance(layout, dict) else None
    if isinstance(rows, list):
        result = []
        seen = set()
        for row in rows:
            if not isinstance(row, list):
                continue
            clean = [key for key in row if key in valid and key not in seen]
            if clean:
                result.append(clean)
                seen.update(clean)
        return result
    order = [key for key in (layout.get("order", []) if isinstance(layout, dict) else []) if key in valid]
    order += [key for key in HOME_BUTTONS if key not in order]
    columns = max(1, min(int((layout or {}).get("columns", 2)), 3))
    return [order[i:i + columns] for i in range(0, len(order), columns)]


def get_home_layout():
    layout = dict(HOME_DEFAULT_LAYOUT)
    try:
        connection = get_db()
        row = connection.execute("SELECT value FROM app_settings WHERE key='home_layout'").fetchone()
        connection.close()
        if row and row["value"]:
            saved = json.loads(row["value"])
            rows = home_layout_rows(saved)
            used = {key for item in rows for key in item}
            rows += [[key] for key in HOME_BUTTONS if key not in used]
            layout = {"rows": rows, "order": [key for item in rows for key in item], "columns": int(saved.get("columns", 2))}
    except (sqlite3.Error, ValueError, TypeError, json.JSONDecodeError):
        pass
    return layout


def get_main_keyboard():
    layout = get_home_layout()
    rows = [
        [KeyboardButton(text=HOME_BUTTONS[key]) for key in row]
        for row in home_layout_rows(layout)
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


main_keyboard = get_main_keyboard()


admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🛍 مدیریت محصولات"),
            KeyboardButton(text="👥 مدیریت کاربران"),
        ],
        [
            KeyboardButton(text="⚙️ تنظیم تست پنلی"),
            KeyboardButton(text="📢 پیام همگانی"),
        ],
        [
            KeyboardButton(text="🎬 مدیریت آموزش اتصال"),
            KeyboardButton(text="💾 بک‌آپ دیتابیس"),
        ],
        [
            KeyboardButton(text="🛡 مدیریت ادمین‌ها"),
        ],
        [
            KeyboardButton(text="🌐 مدیریت پنل‌های VPN"),
        ],
        [
            KeyboardButton(text="🔙 خروج از پنل"),
        ],
    ],
    resize_keyboard=True,
)



cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="❌ لغو"),
        ]
    ],
    resize_keyboard=True,
)


def products_keyboard():
    buttons = []

    products = get_products()
    grouped = {}
    for product in products:
        grouped.setdefault(product['category_name'] or 'محصولات دستی', []).append(product)

    for category_name, category_products in grouped.items():
        buttons.append([InlineKeyboardButton(text=f"📁 {category_name}", callback_data="noop")])
        for product in category_products:
            stock = get_stock(product["id"])
            buttons.append([
                InlineKeyboardButton(
                    text=f"{product['name']} | {product['price']:,.0f} تومان | موجودی: {'∞' if product['category_id'] else stock}",
                    callback_data=f"buy:{product['id']}",
                )
            ])

    buttons.append([InlineKeyboardButton(text="❌ بستن", callback_data="close_message")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def product_management_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ ساخت محصول پنلی", callback_data="product_create")],
        [InlineKeyboardButton(text="✏️ ویرایش Config", callback_data="product_edit_list")],
        [InlineKeyboardButton(text="📊 گزارش محصولات پنلی", callback_data="product_report")],
        [InlineKeyboardButton(text="🗑 غیرفعال‌کردن محصول", callback_data="product_delete_list")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_back")],
    ])


def product_delete_keyboard():
    buttons = []
    for product in get_products():
        buttons.append([InlineKeyboardButton(
            text=f"🗑 {product['name']}", callback_data=f"product_delete:{product['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="product_management")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def product_edit_keyboard():
    buttons = []
    for product in get_products():
        buttons.append([InlineKeyboardButton(
            text=f"✏️ {product['name']}", callback_data=f"product_edit:{product['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="product_management")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_products_keyboard():
    buttons = []
    products = get_products()
    for product in products:
        label = f"🌐 {product['name']} | {product['price']:,.0f} تومان | پنلی"
        buttons.append([InlineKeyboardButton(
            text=label, callback_data=f"stock_product:{product['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="❌ بستن", callback_data="close_message")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def payment_keyboard(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 ارسال رسید پرداخت",
                    callback_data=(
                        f"send_receipt:{order_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ لغو سفارش",
                    callback_data=(
                        f"cancel_order:{order_id}"
                    ),
                )
            ],
        ]
    )


def admin_order_keyboard(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ تأیید پرداخت",
                    callback_data=(
                        f"approve_order:{order_id}"
                    ),
                ),
                InlineKeyboardButton(
                    text="❌ رد پرداخت",
                    callback_data=(
                        f"reject_order:{order_id}"
                    ),
                ),
            ]
        ]
    )


USERS_PER_PAGE = 8


def user_management_keyboard(telegram_id: int, page: int = 0):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ افزایش موجودی",
                    callback_data=(
                        f"balance_add:{telegram_id}"
                    ),
                ),
                InlineKeyboardButton(
                    text="➖ کاهش موجودی",
                    callback_data=(
                        f"balance_sub:{telegram_id}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="♻️ ریست اکانت تست",
                    callback_data=(
                        f"reset_trial:{telegram_id}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت به لیست",
                    callback_data=f"users_list:{page}",
                ),
                InlineKeyboardButton(
                    text="❌ بستن",
                    callback_data="close_message",
                ),
            ],
        ]
    )


def users_list_keyboard(page: int = 0):
    users = get_users()

    total = len(users)
    start = page * USERS_PER_PAGE
    end = start + USERS_PER_PAGE
    page_users = users[start:end]

    buttons = []

    for user in page_users:
        display_name = (
            user["first_name"]
            or (
                "@" + user["username"]
                if user["username"]
                else "بدون نام"
            )
        )

        label = f"{display_name} | {user['telegram_id']}"

        if len(label) > 55:
            label = label[:52] + "…"

        buttons.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=(
                        f"user_view:{user['telegram_id']}:{page}"
                    ),
                )
            ]
        )

    nav_row = []

    if page > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="◀️ قبلی",
                callback_data=f"users_list:{page - 1}",
            )
        )

    if end < total:
        nav_row.append(
            InlineKeyboardButton(
                text="بعدی ▶️",
                callback_data=f"users_list:{page + 1}",
            )
        )

    if nav_row:
        buttons.append(nav_row)

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔍 جستجو با آیدی",
                callback_data="users_search",
            )
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton(
                text="❌ بستن",
                callback_data="close_message",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons), total


def buy_payment_method_keyboard(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👛 پرداخت با کیف پول",
                    callback_data=(
                        f"pay_wallet:{order_id}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💳 پرداخت کارت‌به‌کارت",
                    callback_data=(
                        f"pay_card:{order_id}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ لغو سفارش",
                    callback_data=(
                        f"cancel_order:{order_id}"
                    ),
                )
            ],
        ]
    )


def account_panel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ شارژ کیف پول",
                    callback_data="topup_start",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ بستن",
                    callback_data="close_message",
                )
            ],
        ]
    )


def panel_management_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ افزودن پنل", callback_data="xui_panel_add")],
            [InlineKeyboardButton(text="📋 فهرست پنل‌ها و وضعیت سرور", callback_data="xui_panels")],
            [InlineKeyboardButton(text="🗂 مدیریت دسته‌بندی‌ها", callback_data="xui_categories")],
            [InlineKeyboardButton(text="❌ بستن", callback_data="close_message")],
        ]
    )


def xui_panels_keyboard():
    connection = get_db()
    rows = connection.execute("SELECT id, name, active FROM xui_panels ORDER BY id DESC").fetchall()
    connection.close()
    buttons = []
    for row in rows:
        panel_id = int(row["id"])
        buttons.append([InlineKeyboardButton(
            text=f"{row['name']} | 🖥 وضعیت سرور",
            callback_data=f"xui_panel_view:{panel_id}"
        )])
        buttons.append([InlineKeyboardButton(
            text=f"🗑 حذف {row['name']}", callback_data=f"xui_panel_delete:{panel_id}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="xui_management")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def xui_panel_options_keyboard(panel_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 تغییر لینک Subscription", callback_data=f"xui_panel_suburl:{panel_id}")],
        [InlineKeyboardButton(text="🗑 حذف این پنل", callback_data=f"xui_panel_delete:{panel_id}")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="xui_panels")],
    ])


def xui_categories_keyboard():
    connection = get_db()
    rows = connection.execute(
        """
        SELECT categories.id, categories.name, xui_panels.name AS panel_name
        FROM categories LEFT JOIN xui_panels ON xui_panels.id = categories.panel_id
        WHERE categories.active = 1 ORDER BY categories.id DESC
        """
    ).fetchall()
    connection.close()
    buttons = []
    for row in rows:
        buttons.append([InlineKeyboardButton(
            text=f"{row['name']} ← {row['panel_name'] or 'بدون پنل'}",
            callback_data=f"xui_category_view:{row['id']}"
        )])
        buttons.append([InlineKeyboardButton(
            text=f"🗑 حذف دسته «{row['name']}»", callback_data=f"xui_category_delete:{row['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="➕ افزودن دسته‌بندی", callback_data="xui_category_add")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="xui_management")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def xui_panel_select_keyboard():
    connection = get_db()
    rows = connection.execute("SELECT id, name FROM xui_panels WHERE active = 1 ORDER BY name").fetchall()
    connection.close()
    buttons = [[InlineKeyboardButton(text=row["name"], callback_data=f"xui_category_panel:{row['id']}")] for row in rows]
    buttons.append([InlineKeyboardButton(text="❌ بستن", callback_data="close_message")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def xui_inbounds_keyboard(inbounds: list[dict], selected: list[int] | None = None):
    selected = selected or []
    buttons = []
    for item in inbounds:
        icon = "✅" if item["id"] in selected else "⭕️"
        label = f"{icon} {item['id']} | {item['remark']} | {item['protocol']}:{item['port']}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"xui_inbound_toggle:{item['id']}")])
    buttons.append([InlineKeyboardButton(text="💾 ذخیره دسته‌بندی", callback_data="xui_category_save")])
    buttons.append([InlineKeyboardButton(text="❌ بستن", callback_data="close_message")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def topup_payment_keyboard(topup_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 ارسال رسید پرداخت",
                    callback_data=(
                        f"send_topup_receipt:{topup_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ لغو درخواست",
                    callback_data=(
                        f"cancel_topup:{topup_id}"
                    ),
                )
            ],
        ]
    )


def admin_topup_keyboard(topup_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ تأیید شارژ",
                    callback_data=(
                        f"approve_topup:{topup_id}"
                    ),
                ),
                InlineKeyboardButton(
                    text="❌ رد شارژ",
                    callback_data=(
                        f"reject_topup:{topup_id}"
                    ),
                ),
            ]
        ]
    )


def tutorial_os_keyboard():
    buttons = []

    for os_key, os_data in TUTORIAL_STRUCTURE.items():
        buttons.append(
            [
                InlineKeyboardButton(
                    text=os_data["label"],
                    callback_data=f"tut_os:{os_key}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="❌ بستن",
                callback_data="close_message",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def tutorial_client_keyboard(os_key: str):
    os_data = TUTORIAL_STRUCTURE.get(os_key)

    buttons = []

    if os_data:
        for client_key, client_label in os_data["clients"].items():
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=client_label,
                        callback_data=(
                            f"tut_client:{os_key}:{client_key}"
                        ),
                    )
                ]
            )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت",
                callback_data="tut_back_os",
            ),
            InlineKeyboardButton(
                text="❌ بستن",
                callback_data="close_message",
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_tutorial_os_keyboard():
    buttons = []

    for os_key, os_data in TUTORIAL_STRUCTURE.items():
        buttons.append(
            [
                InlineKeyboardButton(
                    text=os_data["label"],
                    callback_data=f"admin_tut_os:{os_key}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="❌ بستن",
                callback_data="close_message",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_tutorial_client_keyboard(os_key: str):
    os_data = TUTORIAL_STRUCTURE.get(os_key)

    buttons = []

    if os_data:
        videos = get_all_tutorial_videos()

        for client_key, client_label in os_data["clients"].items():
            has_video = (os_key, client_key) in videos

            status_icon = "✅" if has_video else "⭕️"

            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"{status_icon} {client_label}",
                        callback_data=(
                            f"admin_tut_client:{os_key}:{client_key}"
                        ),
                    )
                ]
            )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت",
                callback_data="admin_tut_back_os",
            ),
            InlineKeyboardButton(
                text="❌ بستن",
                callback_data="close_message",
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_management_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ افزودن ادمین",
                    callback_data="admin_add_start",
                )
            ],
            [
                InlineKeyboardButton(
                    text="➖ حذف ادمین",
                    callback_data="admin_remove_start",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ بستن",
                    callback_data="close_message",
                )
            ],
        ]
    )


# =========================================================
# دیتابیس کاربران
# =========================================================

def get_users():
    connection = get_db()

    users = connection.execute(
        """
        SELECT *
        FROM users
        ORDER BY id DESC
        """
    ).fetchall()

    connection.close()
    return users


def get_user(telegram_id: int):
    connection = get_db()

    user = connection.execute(
        """
        SELECT *
        FROM users
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    ).fetchone()

    connection.close()
    return user


def get_user_order_count(telegram_id: int) -> int:
    connection = get_db()

    count = connection.execute(
        """
        SELECT COUNT(*)
        FROM orders
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    ).fetchone()[0]

    connection.close()
    return count


def get_user_approved_orders(telegram_id: int):
    connection = get_db()

    orders = connection.execute(
        """
        SELECT
            orders.*,
            products.name AS product_name,
            products.duration_days,
            products.volume_gb,
            products.category_id,
            xui_panels.base_url,
            xui_panels.api_token,
            xui_panels.subscription_url,
            categories.inbound_ids
        FROM orders
        JOIN products ON products.id = orders.product_id
        LEFT JOIN categories ON categories.id = products.category_id
        LEFT JOIN xui_panels ON xui_panels.id = categories.panel_id
        WHERE orders.telegram_id = ?
        AND orders.status = 'approved'
        ORDER BY orders.id DESC
        """,
        (telegram_id,),
    ).fetchall()

    connection.close()
    return orders


def adjust_balance(
    telegram_id: int,
    amount: float,
    tx_type: str,
    admin_id: int | None = None,
    note: str | None = None,
):
    """
    amount مثبت = افزایش، amount منفی = کاهش.
    برای جلوگیری از منفی‌شدن موجودی هنگام کاهش یا خرید، در یک
    تراکنش امن بررسی و اعمال می‌شود.
    """

    connection = get_db()

    try:
        connection.execute("BEGIN IMMEDIATE")

        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE telegram_id = ?
            """,
            (telegram_id,),
        ).fetchone()

        if user is None:
            connection.rollback()

            return {
                "success": False,
                "message": "کاربر پیدا نشد.",
            }

        new_balance = float(user["balance"]) + amount

        if new_balance < 0:
            connection.rollback()

            return {
                "success": False,
                "message": "موجودی کافی نیست.",
            }

        connection.execute(
            """
            UPDATE users
            SET balance = ?, updated_at = ?
            WHERE telegram_id = ?
            """,
            (
                new_balance,
                now_text(),
                telegram_id,
            ),
        )

        connection.execute(
            """
            INSERT INTO wallet_transactions (
                telegram_id,
                amount,
                type,
                note,
                admin_id,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                telegram_id,
                amount,
                tx_type,
                note,
                admin_id,
                now_text(),
            ),
        )

        connection.commit()

        return {
            "success": True,
            "new_balance": new_balance,
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# =========================================================
# دیتابیس محصولات
# =========================================================

def create_product(
    name: str,
    duration_days: int,
    volume_gb: float,
    price: float,
    category_id: int | None = None,
):
    if category_id is None:
        return None
    connection = get_db()

    try:
        category = connection.execute("SELECT id FROM categories WHERE id=? AND active=1", (category_id,)).fetchone()
        panel = connection.execute("SELECT p.id FROM xui_panels p JOIN categories c ON c.panel_id=p.id WHERE c.id=? AND p.active=1", (category_id,)).fetchone()
        if category is None or panel is None:
            connection.close()
            return None
        cursor = connection.execute(
            """
            INSERT INTO products (
                name,
                duration_days,
                volume_gb,
                price,
                category_id,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                duration_days,
                volume_gb,
                price,
                category_id,
                now_text(),
            ),
        )

        connection.commit()
        product_id = cursor.lastrowid

    except sqlite3.IntegrityError:
        connection.close()
        return None

    connection.close()
    return product_id


def update_product(
    product_id: int,
    name: str,
    duration_days: int,
    volume_gb: float,
    price: float,
    category_id: int,
) -> bool:
    """Update a panel-backed product without touching historical orders."""
    name = (name or "").strip()
    try:
        duration_days = int(duration_days)
        volume_gb = float(volume_gb)
        price = float(price)
        category_id = int(category_id)
    except (TypeError, ValueError):
        return False
    if not name or duration_days <= 0 or volume_gb <= 0 or price < 0:
        return False

    connection = get_db()
    try:
        category = connection.execute(
            "SELECT id FROM categories WHERE id=? AND active=1",
            (category_id,),
        ).fetchone()
        panel = connection.execute(
            "SELECT p.id FROM xui_panels p JOIN categories c ON c.panel_id=p.id "
            "WHERE c.id=? AND p.active=1",
            (category_id,),
        ).fetchone()
        if category is None or panel is None:
            return False
        cursor = connection.execute(
            """UPDATE products
               SET name=?, duration_days=?, volume_gb=?, price=?, category_id=?
               WHERE id=? AND active=1""",
            (name, duration_days, volume_gb, price, category_id, product_id),
        )
        connection.commit()
        return cursor.rowcount > 0
    except sqlite3.IntegrityError:
        connection.rollback()
        return False
    finally:
        connection.close()


def get_products():
    connection = get_db()

    products = connection.execute(
        """
        SELECT products.*, categories.name AS category_name,
               categories.panel_id, categories.inbound_ids,
               xui_panels.base_url, xui_panels.api_token,
               xui_panels.subscription_url
        FROM products
        LEFT JOIN categories ON categories.id = products.category_id
        LEFT JOIN xui_panels ON xui_panels.id = categories.panel_id
        WHERE products.active = 1
          AND categories.active = 1
          AND xui_panels.active = 1
        ORDER BY products.id DESC
        """
    ).fetchall()

    connection.close()
    return products


def get_product(product_id: int):
    connection = get_db()

    product = connection.execute(
        """
        SELECT products.*, categories.name AS category_name,
               categories.panel_id, categories.inbound_ids,
               xui_panels.base_url, xui_panels.api_token,
               xui_panels.subscription_url
        FROM products
        LEFT JOIN categories ON categories.id = products.category_id
        LEFT JOIN xui_panels ON xui_panels.id = categories.panel_id
        WHERE products.id = ?
        AND products.active = 1
        AND categories.active = 1
        AND xui_panels.active = 1
        """,
        (product_id,),
    ).fetchone()

    connection.close()
    return product


def get_all_xui_panels(active_only: bool = False):
    connection = get_db()
    query = "SELECT * FROM xui_panels"
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY id DESC"
    rows = connection.execute(query).fetchall()
    connection.close()
    return rows


def get_xui_panel(panel_id: int):
    connection = get_db()
    row = connection.execute("SELECT * FROM xui_panels WHERE id = ?", (panel_id,)).fetchone()
    connection.close()
    return row


def create_xui_panel(name: str, base_url: str, api_token: str, subscription_url: str | None = None):
    connection = get_db()
    try:
        cursor = connection.execute(
            "INSERT INTO xui_panels (name, base_url, api_token, subscription_url, created_at) VALUES (?, ?, ?, ?, ?)",
            (name.strip(), normalize_xui_base_url(base_url), api_token.strip(), (subscription_url or '').strip() or None, now_text()),
        )
        connection.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        connection.close()


def update_xui_panel_subscription_url(panel_id: int, subscription_url: str) -> bool:
    connection = get_db()
    cursor = connection.execute(
        "UPDATE xui_panels SET subscription_url = ? WHERE id = ?",
        (subscription_url.strip(), panel_id),
    )
    connection.commit()
    connection.close()
    return cursor.rowcount > 0


def get_all_categories(active_only: bool = False):
    connection = get_db()
    query = "SELECT * FROM categories"
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY id DESC"
    rows = connection.execute(query).fetchall()
    connection.close()
    return rows


def get_category(category_id: int):
    connection = get_db()
    row = connection.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
    connection.close()
    return row


def create_category(name: str, panel_id: int, inbound_ids: list[int]):
    name = (name or "").strip()
    try:
        normalized_inbounds = sorted({int(value) for value in (inbound_ids or [])})
    except (TypeError, ValueError):
        return None
    if not name or not normalized_inbounds:
        return None

    connection = get_db()
    try:
        panel = connection.execute(
            "SELECT id FROM xui_panels WHERE id = ? AND active = 1",
            (panel_id,),
        ).fetchone()
        if panel is None:
            return None
        cursor = connection.execute(
            """
            INSERT INTO categories (name, panel_id, inbound_ids, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (name, panel_id, json.dumps(normalized_inbounds), now_text()),
        )
        connection.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        connection.close()


def category_inbound_ids(category) -> list[int]:
    try:
        values = json.loads(category["inbound_ids"] or "[]")
        return [int(value) for value in values]
    except (TypeError, ValueError, json.JSONDecodeError):
        return []


def delete_category(category_id: int) -> tuple[bool, str]:
    connection = get_db()
    try:
        connection.execute("BEGIN IMMEDIATE")
        category = connection.execute("SELECT name FROM categories WHERE id = ?", (category_id,)).fetchone()
        if category is None:
            connection.rollback()
            return False, "دسته‌بندی پیدا نشد."
        product_count = connection.execute(
            "SELECT COUNT(*) FROM products WHERE category_id = ? AND active = 1",
            (category_id,),
        ).fetchone()[0]
        if product_count:
            connection.rollback()
            return False, "این دسته‌بندی به محصول فعال متصل است؛ ابتدا محصول را حذف یا به دسته‌بندی دیگری منتقل کن."
        connection.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        connection.commit()
        return True, f"دسته‌بندی «{category['name']}» حذف شد."
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_category_with_panel(category_id: int):
    connection = get_db()
    row = connection.execute(
        """
        SELECT categories.*, xui_panels.base_url, xui_panels.api_token,
               xui_panels.subscription_url AS panel_subscription_url,
               (SELECT subscription_template FROM xui_panel_settings
                WHERE panel_id = xui_panels.id) AS subscription_template,
               xui_panels.name AS panel_name
        FROM categories JOIN xui_panels ON xui_panels.id = categories.panel_id
        WHERE categories.id = ? AND categories.active = 1 AND xui_panels.active = 1
        """,
        (category_id,),
    ).fetchone()
    connection.close()
    return row

# =========================================================
# دیتابیس موجودی
# =========================================================

def get_stock(product_id: int) -> int:
    connection = get_db()

    product = connection.execute(
        "SELECT category_id FROM products WHERE id = ?",
        (product_id,),
    ).fetchone()

    if product and product["category_id"] is not None:
        connection.close()
        return 1

    count = connection.execute(
        """
        SELECT COUNT(*)
        FROM inventory
        WHERE product_id = ?
        AND status = 'available'
        """,
        (product_id,),
    ).fetchone()[0]

    connection.close()
    return count


def add_configs(
    product_id: int,
    configs: list[str],
):
    connection = get_db()

    added = 0
    duplicate = 0

    for config in configs:
        config = config.strip()

        if not config:
            continue

        try:
            connection.execute(
                """
                INSERT INTO inventory (
                    config,
                    product_id,
                    status,
                    added_at
                )
                VALUES (?, ?, 'available', ?)
                """,
                (
                    config,
                    product_id,
                    now_text(),
                ),
            )

            added += 1

        except sqlite3.IntegrityError:
            duplicate += 1

    connection.commit()
    connection.close()

    return added, duplicate


# =========================================================
# دیتابیس موجودی تست رایگان
# =========================================================

def get_trial_stock() -> int:
    connection = get_db()
    setting = connection.execute(
        "SELECT * FROM trial_settings WHERE id = 1"
    ).fetchone()
    if setting and setting["category_id"] and setting["active"]:
        category = connection.execute(
            "SELECT id FROM categories WHERE id = ? AND active = 1",
            (setting["category_id"],),
        ).fetchone()
        connection.close()
        return 1 if category else 0

    connection.close()
    return 0


def add_trial_configs(configs: list[str]):
    connection = get_db()

    added = 0
    duplicate = 0

    for config in configs:
        config = config.strip()

        if not config:
            continue

        try:
            connection.execute(
                """
                INSERT INTO trial_inventory (
                    config,
                    status,
                    added_at
                )
                VALUES (?, 'available', ?)
                """,
                (
                    config,
                    now_text(),
                ),
            )

            added += 1

        except sqlite3.IntegrityError:
            duplicate += 1

    connection.commit()
    connection.close()

    return added, duplicate


def has_claimed_trial(telegram_id: int) -> bool:
    connection = get_db()

    row = connection.execute(
        """
        SELECT id
        FROM trial_claims
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    ).fetchone()

    connection.close()
    return row is not None


def get_user_trial_claim(telegram_id: int):
    connection = get_db()

    row = connection.execute(
        """
        SELECT *
        FROM trial_claims
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    ).fetchone()

    connection.close()
    return row


# =========================================================
# دیتابیس ویدیوهای آموزش اتصال
# =========================================================

def get_tutorial_video(os_key: str, client_key: str):
    connection = get_db()

    row = connection.execute(
        """
        SELECT *
        FROM tutorial_videos
        WHERE os_key = ?
        AND client_key = ?
        """,
        (os_key, client_key),
    ).fetchone()

    connection.close()
    return row


def set_tutorial_video(
    os_key: str,
    client_key: str,
    chat_id: str,
    message_id: int,
):
    connection = get_db()

    connection.execute(
        """
        INSERT INTO tutorial_videos (
            os_key,
            client_key,
            chat_id,
            message_id,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(os_key, client_key)
        DO UPDATE SET
            chat_id = excluded.chat_id,
            message_id = excluded.message_id,
            updated_at = excluded.updated_at
        """,
        (
            os_key,
            client_key,
            chat_id,
            message_id,
            now_text(),
        ),
    )

    connection.commit()
    connection.close()


def get_all_tutorial_videos():
    connection = get_db()

    rows = connection.execute(
        """
        SELECT *
        FROM tutorial_videos
        """
    ).fetchall()

    connection.close()

    return {
        (row["os_key"], row["client_key"]): row
        for row in rows
    }


def get_trial_settings():
    connection = get_db()
    row = connection.execute("SELECT * FROM trial_settings WHERE id = 1").fetchone()
    connection.close()
    return row


def create_xui_subscription(category, email: str, days: int, volume_gb: float, telegram_id: int | None = None):
    async def _create():
        context = dict(category)
        client = XUIClient(context)
        inbound_ids = category_inbound_ids(context)
        if not inbound_ids:
            raise XUIError("برای تست، inbound انتخاب نشده است.")
        requested_sub_id = new_sub_id()
        added = await client.add_client(
            email=email,
            total_gb=volume_gb,
            duration_days=days,
            telegram_id=telegram_id,
            inbound_ids=inbound_ids,
            start_after_first_use=True,
            sub_id=requested_sub_id,
        )
        sub_id = parse_xui_sub_id(added)
        if not sub_id:
            try:
                sub_id = await client.get_client_sub_id(email)
            except XUIError:
                pass
        if not sub_id or str(sub_id) == str(requested_sub_id):
            try:
                verified_client = await client.get_client(email)
                persisted_sub_id = parse_xui_sub_id({"success": True, "obj": verified_client})
            except XUIError:
                persisted_sub_id = None
            if persisted_sub_id:
                sub_id = persisted_sub_id
        if not sub_id:
            raise XUIError("پنل subId نساخت؛ لینک Subscription قابل ارسال نیست.")
        subscription_url = build_subscription_url(context, sub_id)
        if not subscription_url:
            raise XUIError("لینک Subscription نمونهٔ پنل تنظیم نشده است.")
        return {"success": True, "config": subscription_url, "links": [subscription_url], "sub_id": sub_id, "subscription_url": subscription_url}
    return asyncio.run(_create())


def _extract_subscription_data(context: dict, added: dict, client_data: dict | None = None) -> tuple[str | None, str | None]:
    sub_id = parse_xui_sub_id(added) or ((client_data or {}).get("subId") if isinstance(client_data, dict) else None)
    return (str(sub_id) if sub_id else None, build_subscription_url(context, str(sub_id)) if sub_id else None)


async def provision_xui_subscription(context: dict, email: str, days: int, volume_gb: float, telegram_id: int):
    client = XUIClient(context)
    inbound_ids = category_inbound_ids(context)
    if not inbound_ids:
        raise XUIError("برای این محصول inbound انتخاب نشده است.")
    requested_email = email
    for suffix_attempt in range(20):
        candidate_email = requested_email if suffix_attempt == 0 else f"{requested_email}_{suffix_attempt + 1}"
        requested_sub_id = new_sub_id()
        try:
            added = await client.add_client(
                email=candidate_email, total_gb=volume_gb, duration_days=days,
                telegram_id=telegram_id, inbound_ids=inbound_ids,
                start_after_first_use=True, sub_id=requested_sub_id,
            )
            email = candidate_email
            break
        except XUIError as error:
            if "email already in use" not in str(error).lower() and "already exists" not in str(error).lower():
                raise
            if suffix_attempt == 19:
                raise XUIError("برای این کاربر نام یکتای بیشتری در پنل پیدا نشد.") from error
    else:
        raise XUIError("ساخت کلاینت در پنل ناموفق بود.")
    sub_id = parse_xui_sub_id(added)
    if not sub_id:
        try:
            sub_id = await client.get_client_sub_id(email)
        except XUIError:
            pass
    if not sub_id or str(sub_id) == str(requested_sub_id):
        try:
            verified_client = await client.get_client(email)
            persisted_sub_id = parse_xui_sub_id({"success": True, "obj": verified_client})
        except XUIError:
            persisted_sub_id = None
        if persisted_sub_id:
            sub_id = persisted_sub_id
    if not sub_id:
        raise XUIError("پنل subId نساخت؛ لینک Subscription قابل ارسال نیست.")
    subscription_url = build_subscription_url(context, sub_id)
    if not subscription_url:
        raise XUIError("لینک Subscription نمونهٔ پنل تنظیم نشده است.")
    return {"links": [subscription_url], "sub_id": sub_id, "subscription_url": subscription_url, "email": email}


def save_trial_claim(telegram_id: int, config: str):
    connection = get_db()
    try:
        connection.execute(
            "INSERT INTO trial_claims (telegram_id, config, claimed_at) VALUES (?, ?, ?)",
            (telegram_id, config, now_text()),
        )
        connection.commit()
    except sqlite3.IntegrityError:
        connection.rollback()
    finally:
        connection.close()


def claim_trial(telegram_id: int):
    """Create a panel-backed trial; manual trial inventory is disabled."""
    setting = get_trial_settings()
    if not setting or not setting["active"] or not setting["category_id"]:
        return {"success": False, "message": "سرویس تست پنلی هنوز تنظیم نشده است."}
    category = get_category_with_panel(setting["category_id"])
    if category is None or not category_inbound_ids(category):
        return {"success": False, "message": "مدل inbound تست پنلی معتبر نیست."}
    connection = get_db()
    existing = connection.execute("SELECT id FROM trial_claims WHERE telegram_id = ? AND status = 'active'", (telegram_id,)).fetchone()
    connection.close()
    if existing:
        return {"success": False, "message": "شما قبلاً از تست رایگان استفاده کرده‌اید."}
    email = f"trial_{telegram_id}_{secrets.token_hex(3)}"
    result = create_xui_subscription(category, email, int(setting["duration_days"]), float(setting["volume_gb"]), telegram_id=telegram_id)
    subscription_url = result.get("subscription_url") or result.get("config")
    save_trial_claim(telegram_id, subscription_url)
    return {"success": True, "config": subscription_url, "subscription_url": subscription_url, "sub_id": result.get("sub_id"), "xui_email": email}


# =========================================================
# دیتابیس سفارش‌ها
# =========================================================

def get_order(order_id: int):
    connection = get_db()

    order = connection.execute(
        """
        SELECT
            orders.*,
            products.name AS product_name,
            products.duration_days,
            products.volume_gb,
            products.price,
            products.category_id,
            categories.name AS category_name,
            categories.panel_id,
            categories.inbound_ids,
            xui_panels.base_url,
            xui_panels.api_token,
            xui_panels.subscription_url AS panel_subscription_url,
            (SELECT subscription_template FROM xui_panel_settings
             WHERE panel_id = xui_panels.id) AS subscription_template
        FROM orders
        JOIN products ON products.id = orders.product_id
        LEFT JOIN categories ON categories.id = products.category_id
        LEFT JOIN xui_panels ON xui_panels.id = categories.panel_id
        WHERE orders.id = ?
        """,
        (order_id,),
    ).fetchone()

    connection.close()
    return order


def get_active_order(telegram_id: int, product_id: int):
    """Return only an unpaid order that is still within its payment window."""
    connection = get_db()
    order = connection.execute(
        """
        SELECT orders.*, products.category_id
        FROM orders JOIN products ON products.id = orders.product_id
        WHERE orders.telegram_id = ?
          AND orders.product_id = ?
          AND orders.status IN ('pending_payment', 'pending_admin')
          AND orders.expires_at > ?
        ORDER BY orders.id DESC
        LIMIT 1
        """,
        (telegram_id, product_id, now_text()),
    ).fetchone()
    connection.close()
    return order


def expire_unpaid_orders(telegram_id: int, product_id: int) -> int:
    """Close stale unpaid orders before creating a new order."""
    connection = get_db()
    cursor = connection.execute(
        """
        UPDATE orders SET status = 'expired'
        WHERE telegram_id = ? AND product_id = ?
          AND status IN ('pending_payment', 'pending_admin')
          AND expires_at <= ?
        """,
        (telegram_id, product_id, now_text()),
    )
    connection.commit()
    connection.close()
    return cursor.rowcount


def create_order(
    telegram_id: int,
    product_id: int,
):
    product = get_product(product_id)

    if product is None:
        return None, "محصول پیدا نشد."

    if product["category_id"] is None and get_stock(product_id) <= 0:
        return None, "موجودی محصول تمام شده است."

    old_order = get_active_order(
        telegram_id,
        product_id,
    )

    if old_order:
        return old_order, None

    expire_unpaid_orders(telegram_id, product_id)

    created_at = datetime.now()

    expires_at = created_at + timedelta(
        minutes=AUTO_APPROVE_MINUTES
    )

    connection = get_db()

    cursor = connection.execute(
        """
        INSERT INTO orders (
            telegram_id,
            product_id,
            amount,
            status,
            created_at,
            expires_at,
            duration_days,
            volume_gb
        )
        VALUES (
            ?, ?, ?, 'pending_payment', ?, ?, ?, ?
        )
        """,
        (
            telegram_id,
            product_id,
            float(product["price"]),
            created_at.isoformat(
                timespec="seconds"
            ),
            expires_at.isoformat(
                timespec="seconds"
            ),
            int(product["duration_days"]) if product["duration_days"] is not None else 0,
            float(product["volume_gb"]) if product["volume_gb"] is not None else 0.0,
        ),
    )

    connection.commit()

    order = connection.execute(
        """
        SELECT *
        FROM orders
        WHERE id = ?
        """,
        (cursor.lastrowid,),
    ).fetchone()

    connection.close()

    return order, None


def update_order_proof(
    order_id: int,
    proof_type: str,
    proof_file_id: str | None = None,
    proof_text: str | None = None,
):
    connection = get_db()

    cursor = connection.execute(
        """
        UPDATE orders
        SET
            status = 'pending_admin',
            proof_type = ?,
            proof_file_id = ?,
            proof_text = ?
        WHERE id = ?
        AND status = 'pending_payment'
        """,
        (
            proof_type,
            proof_file_id,
            proof_text,
            order_id,
        ),
    )

    connection.commit()

    updated = cursor.rowcount > 0

    connection.close()
    return updated


def cancel_order(
    order_id: int,
    telegram_id: int,
):
    connection = get_db()

    cursor = connection.execute(
        """
        UPDATE orders
        SET status = 'cancelled'
        WHERE id = ?
        AND telegram_id = ?
        AND status IN (
            'pending_payment',
            'pending_admin'
        )
        """,
        (
            order_id,
            telegram_id,
        ),
    )

    connection.commit()

    cancelled = cursor.rowcount > 0

    connection.close()
    return cancelled


def get_latest_waiting_order(
    telegram_id: int,
):
    connection = get_db()

    order = connection.execute(
        """
        SELECT *
        FROM orders
        WHERE telegram_id = ?
        AND status = 'pending_payment'
        ORDER BY id DESC
        LIMIT 1
        """,
        (telegram_id,),
    ).fetchone()

    connection.close()
    return order


def get_expired_orders():
    connection = get_db()
    orders = connection.execute(
        """
        SELECT id
        FROM orders
        WHERE status = 'pending_admin'
        AND expires_at <= ?
        ORDER BY id ASC
        """,
        (now_text(),),
    ).fetchall()
    connection.close()
    return orders


def approve_manual_order(
    order_id: int,
    approved_by: int,
):
    """
    تأیید سفارش و کم‌کردن موجودی در یک تراکنش انجام می‌شود.
    به این ترتیب دو ادمین نمی‌توانند یک کانفیگ را همزمان بفروشند.
    """

    connection = get_db()

    try:
        connection.execute(
            "BEGIN IMMEDIATE"
        )

        order = connection.execute(
            """
            SELECT
                orders.*,
                products.name AS product_name,
                products.duration_days,
                products.volume_gb,
                products.price
            FROM orders
            JOIN products
                ON products.id = orders.product_id
            WHERE orders.id = ?
            """,
            (order_id,),
        ).fetchone()

        if order is None:
            connection.rollback()

            return {
                "success": False,
                "message": "سفارش پیدا نشد.",
            }

        # اول اسنپ‌شات خود سفارش (لحظه خرید)، سپس fallback روی جدول محصول.
        duration_days = None
        volume_gb = None
        if order["duration_days"] is not None:
            try:
                duration_days = int(order["duration_days"])
            except (TypeError, ValueError):
                duration_days = None
        if order["volume_gb"] is not None:
            try:
                volume_gb = float(order["volume_gb"])
            except (TypeError, ValueError):
                volume_gb = None
        if duration_days is None:
            duration_days = int(order["duration_days"]) if order["duration_days"] is not None else 0
        if volume_gb is None:
            volume_gb = float(order["volume_gb"]) if order["volume_gb"] is not None else 0.0

        if order["status"] == "approved":
            connection.rollback()

            return {
                "success": False,
                "message": "این سفارش قبلاً تأیید شده است.",
            }

        if order["status"] == "rejected":
            connection.rollback()

            return {
                "success": False,
                "message": "این سفارش قبلاً رد شده است.",
            }

        if order["status"] == "cancelled":
            connection.rollback()

            return {
                "success": False,
                "message": "این سفارش لغو شده است.",
            }

        inventory = connection.execute(
            """
            SELECT *
            FROM inventory
            WHERE product_id = ?
            AND status = 'available'
            ORDER BY id ASC
            LIMIT 1
            """,
            (order["product_id"],),
        ).fetchone()

        if inventory is None:
            connection.rollback()

            return {
                "success": False,
                "message": "موجودی این محصول تمام شده است.",
            }

        approved_at = now_text()

        connection.execute(
            """
            UPDATE inventory
            SET
                status = 'sold',
                sold_to = ?,
                sold_at = ?
            WHERE id = ?
            AND status = 'available'
            """,
            (
                order["telegram_id"],
                approved_at,
                inventory["id"],
            ),
        )

        connection.execute(
            """
            UPDATE orders
            SET
                status = 'approved',
                approved_at = ?,
                approved_by = ?,
                delivered_config = ?
            WHERE id = ?
            """,
            (
                approved_at,
                approved_by,
                inventory["config"],
                order_id,
            ),
        )

        connection.commit()

        return {
            "success": True,
            "telegram_id": order["telegram_id"],
            "product_name": order["product_name"],
            "duration_days": duration_days,
            "volume_gb": volume_gb,
            "price": order["price"],
            "config": inventory["config"],
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def _xui_order_context(order_id: int):
    connection = get_db()
    row = connection.execute(
        """
        SELECT orders.*, products.name AS product_name, products.duration_days,
               products.volume_gb, products.price, products.category_id,
               categories.inbound_ids, categories.panel_id,
               xui_panels.base_url, xui_panels.api_token,
               xui_panels.subscription_url AS panel_subscription_url,
               (SELECT subscription_template FROM xui_panel_settings
                WHERE panel_id = xui_panels.id) AS subscription_template
        FROM orders
        JOIN products ON products.id = orders.product_id
        JOIN categories ON categories.id = products.category_id
        JOIN xui_panels ON xui_panels.id = categories.panel_id
        WHERE orders.id = ? AND products.category_id IS NOT NULL
          AND categories.active = 1 AND xui_panels.active = 1
        """,
        (order_id,),
    ).fetchone()
    connection.close()
    return row


def _set_order_xui_pending(order_id: int):
    connection = get_db()
    cursor = connection.execute(
        "UPDATE orders SET status = 'provisioning' WHERE id = ? AND status IN ('pending_admin', 'pending_payment')",
        (order_id,),
    )
    connection.commit()
    connection.close()
    return cursor.rowcount > 0


def _mark_order_xui_failed(order_id: int):
    connection = get_db()
    connection.execute("UPDATE orders SET status = 'pending_admin' WHERE id = ? AND status = 'provisioning'", (order_id,))
    connection.commit()
    connection.close()


def _finish_xui_order(order_id: int, approved_by: int, email: str, links: list[str], sub_id: str | None = None, subscription_url: str | None = None):
    connection = get_db()
    try:
        connection.execute("BEGIN IMMEDIATE")
        order = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if order is None or order["status"] != "provisioning":
            connection.rollback()
            return {"success": False, "message": "این سفارش دیگر قابل پردازش نیست."}
        # مدت/حجم اول از اسنپ‌شات خود سفارش (لحظه خرید) خوانده می‌شود تا
        # ویرایش یا حذف محصول روی سفارش‌های قدیمی اثر نگذارد. اگر دیتابیس
        # قدیمی است و ستون خالی است، از جدول products می‌خوانیم.
        product = connection.execute(
            """SELECT products.name, products.duration_days, products.volume_gb
               FROM products WHERE products.id = ?""", (order["product_id"],)).fetchone()
        product_name = product["name"] if product is not None else "اشتراک"
        duration_days = int(product["duration_days"]) if product is not None and product["duration_days"] is not None else 0
        volume_gb = float(product["volume_gb"]) if product is not None and product["volume_gb"] is not None else 0.0
        if order["duration_days"] is not None:
            try:
                duration_days = int(order["duration_days"])
            except (TypeError, ValueError):
                pass
        if order["volume_gb"] is not None:
            try:
                volume_gb = float(order["volume_gb"])
            except (TypeError, ValueError):
                pass
        if duration_days <= 0 and product is not None:
            duration_days = int(product["duration_days"] or 0)
        if volume_gb <= 0 and product is not None:
            volume_gb = float(product["volume_gb"] or 0.0)
        delivered = "\n".join(links)
        approved_at = now_text()
        connection.execute(
            """
            UPDATE orders SET status = 'approved', approved_at = ?, approved_by = ?,
                delivered_config = ?, xui_email = ?, subscription_url = ?, sub_id = ? WHERE id = ?
            """,
            (approved_at, approved_by, delivered, email, subscription_url, sub_id, order_id),
        )
        connection.commit()
        return {
            "success": True,
            "telegram_id": order["telegram_id"],
            "product_name": product_name,
            "duration_days": duration_days,
            "volume_gb": volume_gb,
            "price": order["amount"],
            "config": delivered,
            "xui_email": email,
            "links": links,
            "subscription_url": subscription_url,
            "sub_id": sub_id,
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


async def approve_xui_order(order_id: int, approved_by: int):
    context = _xui_order_context(order_id)
    if context is None:
        return None
    if context["status"] == "approved":
        return {"success": False, "message": "این سفارش قبلاً تأیید شده است."}
    if not _set_order_xui_pending(order_id):
        return {"success": False, "message": "این سفارش دیگر قابل پردازش نیست."}
    email = make_client_name_for_user(context["telegram_id"], order_id)
    try:
        provisioned = await provision_xui_subscription(
            dict(context), email, int(context["duration_days"]),
            float(context["volume_gb"]), int(context["telegram_id"]),
        )
        return _finish_xui_order(
            order_id, approved_by, email, provisioned["links"],
            provisioned.get("sub_id"), provisioned.get("subscription_url"),
        )
    except Exception:
        _mark_order_xui_failed(order_id)
        raise


async def pay_xui_order_with_wallet(order_id: int):
    context = _xui_order_context(order_id)
    if context is None:
        return None
    connection = get_db()
    try:
        connection.execute("BEGIN IMMEDIATE")
        order = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        user = connection.execute("SELECT * FROM users WHERE telegram_id = ?", (context["telegram_id"],)).fetchone()
        if order is None or order["status"] != "pending_payment":
            connection.rollback()
            return {"success": False, "message": "این سفارش دیگر قابل پرداخت نیست."}
        if user is None or float(user["balance"]) < float(order["amount"]):
            connection.rollback()
            return {"success": False, "message": "موجودی کیف پول کافی نیست."}
        connection.execute("UPDATE users SET balance = balance - ?, updated_at = ? WHERE telegram_id = ?", (order["amount"], now_text(), context["telegram_id"]))
        connection.execute("INSERT INTO wallet_transactions (telegram_id, amount, type, note, created_at) VALUES (?, ?, 'purchase', ?, ?)", (context["telegram_id"], -float(order["amount"]), f"خرید سفارش #{order_id}", now_text()))
        connection.execute("UPDATE orders SET status = 'provisioning' WHERE id = ?", (order_id,))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    email = make_client_name_for_user(context["telegram_id"], order_id)
    try:
        provisioned = await provision_xui_subscription(
            dict(context), email, int(context["duration_days"]),
            float(context["volume_gb"]), int(context["telegram_id"]),
        )
        return _finish_xui_order(
            order_id, 0, email, provisioned["links"],
            provisioned.get("sub_id"), provisioned.get("subscription_url"),
        )
    except Exception:
        _mark_order_xui_failed(order_id)
        # در صورت شکست ساخت کلاینت، مبلغ به کیف پول برمی‌گردد.
        adjust_balance(context["telegram_id"], float(context["amount"]), "refund", note=f"بازگشت سفارش #{order_id}")
        raise


def approve_order(order_id: int, approved_by: int):
    return approve_manual_order(order_id, approved_by)


def pay_order_with_wallet(order_id: int):
    """پرداخت محصول دستی از کیف پول در یک تراکنش امن."""
    connection = get_db()
    try:
        connection.execute("BEGIN IMMEDIATE")
        order = connection.execute(
            """
            SELECT orders.*, products.name AS product_name,
                   products.duration_days, products.volume_gb, products.price,
                   products.category_id
            FROM orders JOIN products ON products.id = orders.product_id
            WHERE orders.id = ?
            """,
            (order_id,),
        ).fetchone()
        if order is None:
            connection.rollback()
            return {"success": False, "message": "سفارش پیدا نشد."}
        if order["status"] != "pending_payment":
            connection.rollback()
            return {"success": False, "message": "این سفارش دیگر قابل پرداخت نیست."}
        if order["category_id"] is not None:
            connection.rollback()
            return {"success": False, "message": "این محصول باید از مسیر پنل پرداخت شود."}
        user = connection.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (order["telegram_id"],)
        ).fetchone()
        inventory = connection.execute(
            """
            SELECT * FROM inventory
            WHERE product_id = ? AND status = 'available'
            ORDER BY id ASC LIMIT 1
            """,
            (order["product_id"],),
        ).fetchone()
        if user is None:
            connection.rollback()
            return {"success": False, "message": "کاربر پیدا نشد."}
        if float(user["balance"]) < float(order["amount"]):
            connection.rollback()
            return {"success": False, "message": "موجودی کیف پول کافی نیست."}
        if inventory is None:
            connection.rollback()
            return {"success": False, "message": "موجودی این محصول تمام شده است."}
        approved_at = now_text()
        new_balance = float(user["balance"]) - float(order["amount"])
        connection.execute(
            "UPDATE users SET balance = ?, updated_at = ? WHERE telegram_id = ?",
            (new_balance, approved_at, order["telegram_id"]),
        )
        connection.execute(
            """
            INSERT INTO wallet_transactions
                (telegram_id, amount, type, note, admin_id, created_at)
            VALUES (?, ?, 'purchase', ?, NULL, ?)
            """,
            (order["telegram_id"], -float(order["amount"]),
             f"خرید محصول #{order['product_id']} (سفارش #{order_id})", approved_at),
        )
        connection.execute(
            """
            UPDATE inventory SET status = 'sold', sold_to = ?, sold_at = ?
            WHERE id = ? AND status = 'available'
            """,
            (order["telegram_id"], approved_at, inventory["id"]),
        )
        connection.execute(
            """
            UPDATE orders SET status = 'approved', approved_at = ?, approved_by = 0,
                delivered_config = ? WHERE id = ?
            """,
            (approved_at, inventory["config"], order_id),
        )
        connection.commit()
        return {
            "success": True,
            "telegram_id": order["telegram_id"],
            "product_name": order["product_name"],
            "duration_days": order["duration_days"],
            "volume_gb": order["volume_gb"],
            "price": order["price"],
            "config": inventory["config"],
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


# =========================================================
# دیتابیس درخواست‌های شارژ کیف پول
# =========================================================

def get_topup(topup_id: int):
    connection = get_db()

    topup = connection.execute(
        """
        SELECT *
        FROM topup_requests
        WHERE id = ?
        """,
        (topup_id,),
    ).fetchone()

    connection.close()
    return topup


def get_active_topup(telegram_id: int):
    connection = get_db()

    topup = connection.execute(
        """
        SELECT *
        FROM topup_requests
        WHERE telegram_id = ?
        AND status IN (
            'pending_payment',
            'pending_admin'
        )
        ORDER BY id DESC
        LIMIT 1
        """,
        (telegram_id,),
    ).fetchone()

    connection.close()
    return topup


def create_topup_request(
    telegram_id: int,
    amount: float,
):
    old_topup = get_active_topup(telegram_id)

    if old_topup:
        return old_topup

    created_at = datetime.now()

    expires_at = created_at + timedelta(
        minutes=AUTO_APPROVE_MINUTES
    )

    connection = get_db()

    cursor = connection.execute(
        """
        INSERT INTO topup_requests (
            telegram_id,
            amount,
            status,
            created_at,
            expires_at
        )
        VALUES (
            ?, ?, 'pending_payment', ?, ?
        )
        """,
        (
            telegram_id,
            amount,
            created_at.isoformat(timespec="seconds"),
            expires_at.isoformat(timespec="seconds"),
        ),
    )

    connection.commit()

    topup = connection.execute(
        """
        SELECT *
        FROM topup_requests
        WHERE id = ?
        """,
        (cursor.lastrowid,),
    ).fetchone()

    connection.close()

    return topup


def update_topup_proof(
    topup_id: int,
    proof_type: str,
    proof_file_id: str | None = None,
    proof_text: str | None = None,
):
    connection = get_db()

    cursor = connection.execute(
        """
        UPDATE topup_requests
        SET
            status = 'pending_admin',
            proof_type = ?,
            proof_file_id = ?,
            proof_text = ?
        WHERE id = ?
        AND status = 'pending_payment'
        """,
        (
            proof_type,
            proof_file_id,
            proof_text,
            topup_id,
        ),
    )

    connection.commit()

    updated = cursor.rowcount > 0

    connection.close()
    return updated


def cancel_topup(
    topup_id: int,
    telegram_id: int,
):
    connection = get_db()

    cursor = connection.execute(
        """
        UPDATE topup_requests
        SET status = 'cancelled'
        WHERE id = ?
        AND telegram_id = ?
        AND status IN (
            'pending_payment',
            'pending_admin'
        )
        """,
        (
            topup_id,
            telegram_id,
        ),
    )

    connection.commit()

    cancelled = cursor.rowcount > 0

    connection.close()
    return cancelled


def get_expired_topups():
    connection = get_db()

    topups = connection.execute(
        """
        SELECT id
        FROM topup_requests
        WHERE status = 'pending_admin'
        AND expires_at <= ?
        ORDER BY id ASC
        """,
        (now_text(),),
    ).fetchall()

    connection.close()
    return topups


def approve_topup(
    topup_id: int,
    approved_by: int,
):
    """
    تأیید شارژ و افزایش موجودی کیف پول در یک تراکنش امن.
    """

    connection = get_db()

    try:
        connection.execute("BEGIN IMMEDIATE")

        topup = connection.execute(
            """
            SELECT *
            FROM topup_requests
            WHERE id = ?
            """,
            (topup_id,),
        ).fetchone()

        if topup is None:
            connection.rollback()

            return {
                "success": False,
                "message": "درخواست پیدا نشد.",
            }

        if topup["status"] != "pending_admin":
            connection.rollback()

            return {
                "success": False,
                "message": "این درخواست قبلاً بررسی شده است.",
            }

        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE telegram_id = ?
            """,
            (topup["telegram_id"],),
        ).fetchone()

        if user is None:
            connection.rollback()

            return {
                "success": False,
                "message": "کاربر پیدا نشد.",
            }

        approved_at = now_text()

        new_balance = float(user["balance"]) + float(
            topup["amount"]
        )

        connection.execute(
            """
            UPDATE users
            SET balance = ?, updated_at = ?
            WHERE telegram_id = ?
            """,
            (
                new_balance,
                approved_at,
                topup["telegram_id"],
            ),
        )

        connection.execute(
            """
            INSERT INTO wallet_transactions (
                telegram_id,
                amount,
                type,
                note,
                admin_id,
                created_at
            )
            VALUES (?, ?, 'topup', ?, ?, ?)
            """,
            (
                topup["telegram_id"],
                float(topup["amount"]),
                f"شارژ کیف پول (درخواست #{topup_id})",
                approved_by,
                approved_at,
            ),
        )

        connection.execute(
            """
            UPDATE topup_requests
            SET
                status = 'approved',
                approved_at = ?,
                approved_by = ?
            WHERE id = ?
            """,
            (
                approved_at,
                approved_by,
                topup_id,
            ),
        )

        connection.commit()

        return {
            "success": True,
            "telegram_id": topup["telegram_id"],
            "amount": topup["amount"],
            "new_balance": new_balance,
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def reject_topup(
    topup_id: int,
    admin_id: int,
):
    connection = get_db()

    cursor = connection.execute(
        """
        UPDATE topup_requests
        SET
            status = 'rejected',
            rejected_at = ?,
            rejected_by = ?
        WHERE id = ?
        AND status = 'pending_admin'
        """,
        (
            now_text(),
            admin_id,
            topup_id,
        ),
    )

    connection.commit()

    rejected = cursor.rowcount > 0

    connection.close()
    return rejected


def reject_order(
    order_id: int,
    admin_id: int,
):
    connection = get_db()

    cursor = connection.execute(
        """
        UPDATE orders
        SET
            status = 'rejected',
            rejected_at = ?,
            rejected_by = ?
        WHERE id = ?
        AND status = 'pending_admin'
        """,
        (
            now_text(),
            admin_id,
            order_id,
        ),
    )

    connection.commit()

    rejected = cursor.rowcount > 0

    connection.close()
    return rejected


# =========================================================
# ارسال محصول به کاربر
# =========================================================

def subscriptions_keyboard(orders):
    buttons = []
    for order in orders:
        buttons.append([
            InlineKeyboardButton(
                text=f"📊 بررسی مصرف #{order['id']}",
                callback_data=f"subscription_traffic:{order['id']}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="❌ بستن", callback_data="close_message")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def send_subscription_to_user(telegram_id: int, title: str, links: list[str], product_name: str, duration_days: int, volume_gb: float, price: float | None = None):
    if not links:
        raise XUIError("لینک Subscription ساخته نشد.")
    subscription = links[0]
    details = (
        f"📦 محصول: <b>{html.escape(product_name)}</b>\n"
        f"⏳ مدت: <b>{duration_days}</b> روز\n"
        f"📊 حجم: <b>{volume_gb}</b> GB\n"
    )
    if price is not None:
        details += f"💰 مبلغ: <b>{price:,.0f}</b> تومان\n"
    details += "\n🔗 <b>لینک Subscription:</b>\n<code>" + html.escape(subscription) + "</code>"
    caption = f"✅ <b>{html.escape(title)}</b>\n\n{details}\n\n📱 QR Code همین لینک را در برنامه VPN اسکن کن."
    await bot.send_photo(
        telegram_id,
        BufferedInputFile(qr_png_bytes(subscription), filename="subscription-qr.png"),
        caption=caption,
        parse_mode="HTML",
        reply_markup=get_main_keyboard(),
    )


async def send_product_to_user(result: dict):
    if result.get("subscription_url"):
        await send_subscription_to_user(
            result["telegram_id"],
            title="پرداخت تأیید شد.",
            links=[result["subscription_url"]],
            product_name=result["product_name"],
            duration_days=int(result["duration_days"]),
            volume_gb=float(result["volume_gb"]),
            price=float(result.get("price") or 0),
        )
        return
    safe_product_name = html.escape(
        result["product_name"]
    )

    safe_config = html.escape(
        result["config"]
    )

    await bot.send_message(
        result["telegram_id"],
        "✅ <b>پرداخت تأیید شد.</b>\n\n"
        f"📦 محصول: <b>{safe_product_name}</b>\n"
        f"⏳ مدت: <b>{result['duration_days']}</b> روز\n"
        f"📊 حجم: <b>{result['volume_gb']}</b> GB\n"
        f"💰 مبلغ: <b>{result['price']:,.0f}</b> تومان\n\n"
        "🔐 <b>لینک‌های اتصال شما:</b>\n"
        f"<code>{safe_config}</code>\n\n"
        "لینک‌ها را کپی کن و داخل برنامه اتصال وارد کن.",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(),
    )


# =========================================================
# ارسال رسید برای ادمین‌ها
# =========================================================

async def send_order_to_admins(
    order_id: int,
):
    order = get_order(order_id)

    if order is None:
        return

    username_text = "بدون یوزرنیم"

    user = None

    connection = get_db()

    user = connection.execute(
        """
        SELECT *
        FROM users
        WHERE telegram_id = ?
        """,
        (order["telegram_id"],),
    ).fetchone()

    connection.close()

    if user and user["username"]:
        username_text = (
            "@" + html.escape(user["username"])
        )

    proof_text = html.escape(
        order["proof_text"] or "بدون توضیح"
    )

    admin_text = (
        "💳 <b>رسید پرداخت جدید</b>\n\n"
        f"🧾 شماره سفارش: "
        f"<code>{order['id']}</code>\n"
        f"🆔 آیدی کاربر: "
        f"<code>{order['telegram_id']}</code>\n"
        f"👤 یوزرنیم: {username_text}\n"
        f"📦 محصول: "
        f"<b>{html.escape(order['product_name'])}</b>\n"
        f"💰 مبلغ: <b>{order['price']:,.0f}</b> تومان\n"
        f"🔗 نوع اتصال: "
        f"{'خودکار از پنل' if order['category_id'] else 'دستی'}\n"
        f"📝 توضیحات رسید:\n{proof_text}\n\n"
        f"⏰ پایان زمان بررسی: "
        f"<code>{order['expires_at']}</code>"
    )

    for admin_id in ADMIN_IDS:
        try:
            if (
                order["proof_type"] == "photo"
                and order["proof_file_id"]
            ):
                await bot.send_photo(
                    chat_id=admin_id,
                    photo=order["proof_file_id"],
                    caption=admin_text,
                    parse_mode="HTML",
                    reply_markup=admin_order_keyboard(
                        order_id
                    ),
                )
            else:
                await bot.send_message(
                    chat_id=admin_id,
                    text=admin_text,
                    parse_mode="HTML",
                    reply_markup=admin_order_keyboard(
                        order_id
                    ),
                )

        except Exception as error:
            print(
                "خطا در ارسال رسید برای ادمین:",
                error,
            )


# =========================================================
# بک‌آپ دیتابیس
# =========================================================

def create_database_backup() -> Path:
    """
    یک نسخه امن و سازگار از دیتابیس در حال اجرا می‌سازد
    (با sqlite backup API، بدون قفل کردن یا خراب کردن دیتابیس
    اصلی حتی در حین نوشتن هم‌زمان).
    """

    if not DATABASE_FILE.exists():
        return None
    backup_dir = BASE_DIR / "backups"
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"bot_backup_{timestamp}.db"

    source = sqlite3.connect(str(DATABASE_FILE))
    destination = sqlite3.connect(str(backup_path))

    with destination:
        source.backup(destination)

    source.close()
    destination.close()

    prune_database_backups(backup_dir)

    return backup_path


def prune_database_backups(backup_dir: Path, keep: int = 48) -> int:
    """فقط آخرین `keep` بک‌آپ را نگه می‌دارد تا دیسک پر نشود."""

    try:
        backups = sorted(
            (path for path in backup_dir.glob("bot_backup_*.db") if path.is_file()),
            key=lambda path: path.stat().st_mtime,
        )
    except OSError:
        return 0

    removed = 0
    for path in backups[:-keep] if keep > 0 else backups:
        try:
            path.unlink()
            removed += 1
        except OSError:
            pass
    return removed


async def send_backup_to_admins(caption: str):
    try:
        backup_path = create_database_backup()

    except Exception as error:
        print(
            "خطا در ساخت بک‌آپ دیتابیس:",
            error,
        )

        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    "❌ خطا در ساخت بک‌آپ دیتابیس. "
                    "لاگ سرور را بررسی کن.",
                )
            except Exception:
                pass

        return

    backup_file = FSInputFile(backup_path)

    backup_size_kb = max(
        1,
        int(backup_path.stat().st_size / 1024),
    )

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_document(
                chat_id=admin_id,
                document=backup_file,
                caption=caption
                + f"\n📦 حجم فایل: <b>{backup_size_kb:,}</b> کیلوبایت",
                parse_mode="HTML",
            )
        except Exception as error:
            print(
                "خطا در ارسال بک‌آپ به ادمین:",
                error,
            )
            break


async def backup_worker():
    while True:
        await asyncio.sleep(
            BACKUP_INTERVAL_HOURS * 3600
        )

        await send_backup_to_admins(
            "💾 <b>بک‌آپ خودکار دیتابیس</b>\n\n"
            f"🕐 زمان: {now_text()}\n"
            f"🔄 هر {BACKUP_INTERVAL_HOURS} ساعت"
        )


# =========================================================
# تایید خودکار سفارش‌ها
# =========================================================

async def auto_approve_worker():
    while True:
        try:
            expired_orders = get_expired_orders()

            for item in expired_orders:
                order_id = item["id"]
                order = get_order(order_id)
                if order is None:
                    continue

                if order["category_id"] is not None:
                    try:
                        result = await approve_xui_order(
                            order_id=order_id,
                            approved_by=0,
                        )
                    except Exception as error:
                        print("خطا در تأیید خودکار پنلی:", error)
                        continue
                else:
                    result = approve_order(
                        order_id=order_id,
                        approved_by=0,
                    )

                if not result["success"]:
                    continue

                try:
                    await send_product_to_user(
                        result
                    )

                    await bot.send_message(
                        result["telegram_id"],
                        "⏱ چون ادمین تا پایان زمان تعیین‌شده "
                        "رسید را بررسی نکرد، سفارش شما "
                        "به‌صورت خودکار تأیید شد.",
                    )

                except Exception as error:
                    print(
                        "خطا در ارسال سفارش خودکار:",
                        error,
                    )

                for admin_id in ADMIN_IDS:
                    try:
                        await bot.send_message(
                            admin_id,
                            f"⏱ سفارش شماره "
                            f"<code>{order_id}</code> "
                            "به‌صورت خودکار تأیید شد.",
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass

            expired_topups = get_expired_topups()

            for item in expired_topups:
                topup_id = item["id"]

                result = approve_topup(
                    topup_id=topup_id,
                    approved_by=0,
                )

                if not result["success"]:
                    continue

                try:
                    await bot.send_message(
                        result["telegram_id"],
                        "⏱ چون ادمین تا پایان زمان تعیین‌شده "
                        "رسید را بررسی نکرد، شارژ کیف پول شما "
                        "به‌صورت خودکار تأیید شد.\n\n"
                        f"💰 مبلغ: "
                        f"<b>{result['amount']:,.0f}</b> تومان\n"
                        f"👛 موجودی جدید: "
                        f"<b>{result['new_balance']:,.0f}</b> تومان",
                        parse_mode="HTML",
                        reply_markup=get_main_keyboard(),
                    )

                except Exception as error:
                    print(
                        "خطا در ارسال شارژ خودکار:",
                        error,
                    )

                for admin_id in ADMIN_IDS:
                    try:
                        await bot.send_message(
                            admin_id,
                            f"⏱ درخواست شارژ شماره "
                            f"<code>{topup_id}</code> "
                            "به‌صورت خودکار تأیید شد.",
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass

        except Exception as error:
            print(
                "خطا در worker تأیید خودکار:",
                error,
            )

        await asyncio.sleep(30)


# =========================================================
# میان‌افزار عضویت اجباری در کانال
# =========================================================

@dp.message.outer_middleware()
async def membership_message_middleware(handler, event: Message, data):
    if not REQUIRED_CHANNEL:
        return await handler(event, data)

    if is_admin(event.from_user.id):
        return await handler(event, data)

    if event.text and event.text.startswith("/start"):
        return await handler(event, data)

    if await is_channel_member(event.from_user.id):
        return await handler(event, data)

    await event.answer(
        "⛔ <b>برای استفاده از ربات باید عضو کانال ما باشی.</b>\n\n"
        "بعد از عضویت، روی دکمه «✅ عضو شدم» بزن:",
        reply_markup=join_channel_keyboard(),
        parse_mode="HTML",
    )
    return


@dp.callback_query.outer_middleware()
async def membership_callback_middleware(
    handler, event: CallbackQuery, data
):
    if not REQUIRED_CHANNEL:
        return await handler(event, data)

    if is_admin(event.from_user.id):
        return await handler(event, data)

    if event.data == "check_join":
        return await handler(event, data)

    if await is_channel_member(event.from_user.id):
        return await handler(event, data)

    await event.answer(
        "⛔ برای استفاده از ربات باید عضو کانال باشی.",
        show_alert=True,
    )
    return


@dp.callback_query(F.data == "check_join")
async def check_join_callback(
    callback: CallbackQuery,
):
    if await is_channel_member(callback.from_user.id):
        try:
            await callback.message.delete()
        except Exception:
            pass

        await callback.message.answer(
            "✅ عضویت شما تأیید شد. خوش آمدی!",
            reply_markup=get_main_keyboard(),
        )

        await callback.answer(
            "عضویت تأیید شد."
        )
        return

    await callback.answer(
        "هنوز عضو کانال نشده‌ای.",
        show_alert=True,
    )


# =========================================================
# شروع ربات
# =========================================================

@dp.message(CommandStart())
async def start_handler(
    message: Message,
    state: FSMContext,
):
    await state.clear()
    save_user(message.from_user)

    if not is_admin(message.from_user.id) and not (
        await is_channel_member(message.from_user.id)
    ):
        await message.answer(
            "👋 سلام!\n\n"
            "⛔ <b>برای استفاده از ربات باید عضو کانال ما باشی.</b>\n\n"
            "بعد از عضویت، روی دکمه «✅ عضو شدم» بزن:",
            reply_markup=join_channel_keyboard(),
            parse_mode="HTML",
        )
        return

    await message.answer(
        "سلام 👋\n"
        "به ربات فروش اشتراک خوش آمدی.",
        reply_markup=get_main_keyboard(),
    )


# =========================================================
# پنل ادمین
# =========================================================

@dp.message(Command("admin"))
async def admin_handler(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        await message.answer(
            "⛔ شما دسترسی ادمین ندارید."
        )
        return

    await state.clear()

    await message.answer(
        "🛠 پنل مدیریت",
        reply_markup=admin_keyboard,
    )


@dp.message(F.text == "🔙 خروج از پنل")
async def exit_admin_handler(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    await state.clear()

    await message.answer(
        "از پنل مدیریت خارج شدی.",
        reply_markup=get_main_keyboard(),
    )


@dp.message(F.text == "❌ لغو")
async def cancel_handler(
    message: Message,
    state: FSMContext,
):
    await state.clear()

    keyboard = (
        admin_keyboard
        if is_admin(message.from_user.id)
        else main_keyboard
    )

    await message.answer(
        "عملیات لغو شد.",
        reply_markup=keyboard,
    )


# =========================================================
# ساخت محصول
# =========================================================

@dp.callback_query(F.data == "product_management")
async def product_management_callback(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text("🛍 <b>مدیریت محصولات</b>", reply_markup=product_management_keyboard(), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "product_delete_list")
async def product_delete_list_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return
    products = get_products()
    if not products:
        await callback.answer("محصول فعالی وجود ندارد.", show_alert=True)
        return
    await callback.message.edit_text("محصولی را برای حذف/غیرفعال‌کردن انتخاب کن:", reply_markup=product_delete_keyboard())
    await callback.answer()


@dp.callback_query(F.data.startswith("product_delete:"))
async def product_delete_callback(callback: CallbackQuery):
    if not is_super_admin(callback.from_user.id):
        await callback.answer("فقط سوپرادمین مجاز است.", show_alert=True)
        return
    product_id = int(callback.data.split(":")[1])
    product = get_product(product_id)
    if product is None:
        await callback.answer("محصول پیدا نشد.", show_alert=True)
        return
    await callback.message.edit_text(
        f"⚠️ محصول «{html.escape(product['name'])}» غیرفعال شود؟\n\n"
        "پس از آن برای کاربران نمایش داده نمی‌شود و سفارش جدید برایش ساخته نمی‌شود.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ بله، غیرفعال شود", callback_data=f"product_delete_confirm:{product_id}")],
            [InlineKeyboardButton(text="❌ لغو", callback_data="product_delete_list")],
        ]), parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("product_delete_confirm:"))
async def product_delete_confirm_callback(callback: CallbackQuery):
    if not is_super_admin(callback.from_user.id):
        await callback.answer("فقط سوپرادمین مجاز است.", show_alert=True)
        return
    product_id = int(callback.data.split(":")[1])
    connection = get_db()
    cursor = connection.execute("UPDATE products SET active = 0, category_id = NULL WHERE id = ? AND active = 1", (product_id,))
    connection.commit()
    connection.close()
    if cursor.rowcount == 0:
        await callback.answer("محصول پیدا نشد یا قبلاً غیرفعال شده است.", show_alert=True)
        return
    await callback.message.edit_text("✅ محصول غیرفعال شد.", reply_markup=product_management_keyboard())
    await callback.answer("محصول غیرفعال شد.")


@dp.callback_query(F.data == "product_create")
async def product_create_callback(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return
    await callback.answer()
    await create_product_start(callback.message, state, callback.from_user.id)


@dp.callback_query(F.data == "product_report")
async def product_report_callback(callback: CallbackQuery):
    await callback.answer()
    await products_report(callback.message)


@dp.callback_query(F.data == "product_edit_list")
async def product_edit_list_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True); return
    products = get_products()
    if not products:
        await callback.answer("محصول فعالی وجود ندارد.", show_alert=True); return
    await callback.message.edit_text("محصولی را برای ویرایش Config انتخاب کن:", reply_markup=product_edit_keyboard())
    await callback.answer()


@dp.callback_query(F.data.startswith("product_edit:"))
async def product_edit_callback(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True); return
    try: product_id = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("شناسه محصول نامعتبر است.", show_alert=True); return
    product = get_product(product_id)
    if product is None:
        await callback.answer("محصول فعال پیدا نشد.", show_alert=True); return
    await state.clear(); await state.update_data(edit_product_id=product_id, edit_product_category_id=product["category_id"])
    await state.set_state(AdminStates.waiting_product_edit_name)
    await callback.message.answer(f"نام جدید محصول را بفرست. مقدار فعلی: {html.escape(product['name'])}", reply_markup=cancel_keyboard, parse_mode="HTML")
    await callback.answer()


@dp.message(AdminStates.waiting_product_edit_name)
async def receive_product_edit_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    name = (message.text or "").strip()
    if not name: await message.answer("نام نمی‌تواند خالی باشد."); return
    await state.update_data(edit_product_name=name); await state.set_state(AdminStates.waiting_product_edit_days)
    await message.answer("مدت جدید را برحسب روز بفرست:", reply_markup=cancel_keyboard)


@dp.message(AdminStates.waiting_product_edit_days)
async def receive_product_edit_days(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    value = (message.text or "").strip()
    if not value.isdigit() or int(value) <= 0: await message.answer("مدت باید عدد صحیح بیشتر از صفر باشد."); return
    await state.update_data(edit_product_days=int(value)); await state.set_state(AdminStates.waiting_product_edit_volume)
    await message.answer("حجم جدید را برحسب GB بفرست:", reply_markup=cancel_keyboard)


@dp.message(AdminStates.waiting_product_edit_volume)
async def receive_product_edit_volume(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    try: volume = float((message.text or "").strip().replace(",", ""))
    except ValueError: await message.answer("حجم واردشده معتبر نیست."); return
    if volume <= 0: await message.answer("حجم باید بیشتر از صفر باشد."); return
    await state.update_data(edit_product_volume=volume); await state.set_state(AdminStates.waiting_product_edit_price)
    await message.answer("قیمت جدید را برحسب تومان بفرست:", reply_markup=cancel_keyboard)


@dp.message(AdminStates.waiting_product_edit_price)
async def receive_product_edit_price(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    try: price = float((message.text or "").strip().replace(",", ""))
    except ValueError: await message.answer("قیمت واردشده معتبر نیست."); return
    if price < 0: await message.answer("قیمت نمی‌تواند منفی باشد."); return
    data = await state.get_data(); categories = get_all_categories(active_only=True)
    if not categories: await state.clear(); await message.answer("هیچ مدل Inbound فعالی وجود ندارد.", reply_markup=admin_keyboard); return
    await state.update_data(edit_product_price=price); await state.set_state(AdminStates.waiting_product_edit_category)
    buttons = [[InlineKeyboardButton(text=f"🌐 {row['name']} ← پنل {row['panel_id']}", callback_data=f"product_edit_category:{row['id']}")] for row in categories]
    buttons.append([InlineKeyboardButton(text="❌ لغو", callback_data="close_message")])
    await message.answer("مدل Inbound جدید را انتخاب کن:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@dp.callback_query(F.data.startswith("product_edit_category:"))
async def product_edit_category_callback(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): await callback.answer("دسترسی ندارید.", show_alert=True); return
    try: category_id = int(callback.data.split(":", 1)[1])
    except ValueError: await callback.answer("دسته نامعتبر است.", show_alert=True); return
    category = get_category_with_panel(category_id)
    if category is None or not category_inbound_ids(category): await callback.answer("مدل Inbound معتبر نیست.", show_alert=True); return
    data = await state.get_data()
    ok = update_product(data.get("edit_product_id"), data.get("edit_product_name"), data.get("edit_product_days"), data.get("edit_product_volume"), data.get("edit_product_price"), category_id)
    await state.clear()
    await callback.message.edit_text("✅ Config با موفقیت ویرایش شد." if ok else "❌ ویرایش انجام نشد؛ نام تکراری یا محصول نامعتبر است.", reply_markup=product_management_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "product_stock")
async def product_stock_callback(callback: CallbackQuery):
    await callback.answer()
    await add_stock_start(callback.message)


@dp.callback_query(F.data == "admin_back")
async def admin_back_callback(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("پنل مدیریت:", reply_markup=admin_keyboard)


@dp.message(F.text == "🛍 مدیریت محصولات")
async def product_management_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        "🛍 <b>مدیریت محصولات</b>\n\n"
        "محصولات پنلی موجودی دستی ندارند. همه محصولات از پنل ساخته می‌شوند.",
        reply_markup=product_management_keyboard(),
        parse_mode="HTML",
    )


async def create_product_start(
    message: Message,
    state: FSMContext,
    user_id: int | None = None,
):
    actor_id = user_id if user_id is not None else message.from_user.id
    if not is_admin(actor_id):
        return

    await state.set_state(
        AdminStates.waiting_product_name
    )

    await message.answer(
        "نام محصول را ارسال کن:",
        reply_markup=cancel_keyboard,
    )


@dp.message(AdminStates.waiting_product_name)
async def receive_product_name(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    name = message.text.strip()

    if not name:
        await message.answer(
            "نام محصول نمی‌تواند خالی باشد."
        )
        return

    await state.update_data(
        product_name=name
    )

    await state.set_state(
        AdminStates.waiting_product_days
    )

    await message.answer(
        "مدت اشتراک را برحسب روز بفرست.\n"
        "مثال: 30",
        reply_markup=cancel_keyboard,
    )


@dp.message(AdminStates.waiting_product_days)
async def receive_product_days(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    value = message.text.strip()

    if not value.isdigit() or int(value) <= 0:
        await message.answer(
            "مدت باید عدد صحیح بیشتر از صفر باشد."
        )
        return

    await state.update_data(
        product_days=int(value)
    )

    await state.set_state(
        AdminStates.waiting_product_volume
    )

    await message.answer(
        "حجم اشتراک را برحسب GB بفرست.\n"
        "مثال: 100",
        reply_markup=cancel_keyboard,
    )


@dp.message(AdminStates.waiting_product_volume)
async def receive_product_volume(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    value = message.text.strip().replace(
        ",",
        "",
    )

    try:
        volume = Decimal(value)
    except InvalidOperation:
        await message.answer(
            "حجم واردشده معتبر نیست."
        )
        return

    if volume <= 0:
        await message.answer(
            "حجم باید بیشتر از صفر باشد."
        )
        return

    await state.update_data(
        product_volume=float(volume)
    )

    await state.set_state(
        AdminStates.waiting_product_price
    )

    await message.answer(
        "قیمت را برحسب تومان بفرست.\n"
        "مثال: 150000",
        reply_markup=cancel_keyboard,
    )


@dp.message(AdminStates.waiting_product_price)
async def receive_product_price(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    value = message.text.strip().replace(
        ",",
        "",
    )

    try:
        price = Decimal(value)
    except InvalidOperation:
        await message.answer(
            "قیمت واردشده معتبر نیست."
        )
        return

    if price < 0:
        await message.answer(
            "قیمت نمی‌تواند منفی باشد."
        )
        return

    data = await state.get_data()
    await state.update_data(
        product_price=float(price)
    )
    categories = get_all_categories(active_only=True)
    if not categories:
        await state.clear()
        await message.answer(
            "❌ هنوز هیچ مدل Inbound در مدیریت پنل ساخته نشده است.\n"
            "ابتدا از مدیریت پنل‌ها یک دسته‌بندی بساز و Inboundها را انتخاب کن.",
            reply_markup=product_management_keyboard(),
        )
        return
    await state.set_state(AdminStates.waiting_product_category)
    buttons = [[InlineKeyboardButton(text=f"🌐 {row['name']} ← پنل {row['panel_id']}", callback_data=f"product_category:{row['id']}")] for row in categories]
    buttons.append([InlineKeyboardButton(text="❌ لغو", callback_data="close_message")])
    await message.answer(
        "محصول را به کدام مدل Inbound وصل کنم؟\n"
        "Inboundها قبلاً در بخش مدیریت پنل تنظیم شده‌اند.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@dp.callback_query(F.data.startswith("product_category:"))
async def product_category_callback(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return
    value = callback.data.split(":", 1)[1]
    category_id = int(value)
    category = get_category_with_panel(category_id)
    if category is None or not category_inbound_ids(category):
        await callback.answer("مدل Inbound معتبر نیست یا دیگر فعال نیست.", show_alert=True)
        return
    data = await state.get_data()
    product_id = create_product(
        name=data["product_name"],
        duration_days=data["product_days"],
        volume_gb=data["product_volume"],
        price=float(data["product_price"]),
        category_id=category_id,
    )
    await state.clear()
    if product_id is None:
        await callback.message.answer("❌ محصولی با این نام قبلاً وجود دارد.", reply_markup=admin_keyboard)
    else:
        kind = "اتصال‌داده‌شده به مدل Inbound"
        await callback.message.answer(
            f"✅ محصول {kind} با موفقیت ساخته شد.\n\n"
            f"🆔 شناسه محصول: {product_id}\n"
            f"🛍 نام: {html.escape(data['product_name'])}\n"
            f"⏳ مدت: {data['product_days']} روز\n"
            f"📊 حجم: {data['product_volume']} GB\n"
            f"💰 قیمت: {float(data['product_price']):,.0f} تومان",
            reply_markup=admin_keyboard,
            parse_mode="HTML",
        )
    await callback.answer()


@dp.message(AdminStates.waiting_product_category)
async def receive_product_category(message: Message, state: FSMContext):
    await message.answer("لطفاً یکی از دسته‌بندی‌های نمایش‌داده‌شده را انتخاب کن.")



# =========================================================
# افزودن موجودی
# =========================================================

@dp.message(F.text == "📦 افزودن موجودی")
async def add_stock_start(
    message: Message,
):
    if not is_admin(message.from_user.id):
        return

    products = get_products()

    if not products:
        await message.answer(
            "ابتدا باید یک محصول بسازی.",
            reply_markup=admin_keyboard,
        )
        return

    await message.answer(
        "محصول موردنظر را انتخاب کن:",
        reply_markup=admin_products_keyboard(),
    )


@dp.callback_query(F.data.startswith("stock_product:"))
async def stock_product_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "دسترسی ندارید.",
            show_alert=True,
        )
        return

    product_id = int(
        callback.data.split(":")[1]
    )

    product = get_product(product_id)

    if product is None:
        await callback.answer(
            "محصول پیدا نشد.",
            show_alert=True,
        )
        return

    if product["category_id"] is None:
        await state.clear()
        await callback.message.answer(
            "⚠️ این محصول قدیمیِ موجودی دستی است و دیگر قابل مدیریت نیست.\n"
            "محصول را از بخش مدیریت محصولات غیرفعال کن و یک محصول پنلی بساز.",
            reply_markup=admin_keyboard,
        )
        await callback.answer()
        return

    await state.clear()
    await callback.message.answer(
        "🌐 این محصول پنلی است و موجودی دستی ندارد.\n"
        "کلاینت هنگام پرداخت از پنل 3x-ui ساخته می‌شود.",
        reply_markup=admin_keyboard,
    )
    await callback.answer()
    return


@dp.message(AdminStates.waiting_stock_configs)
async def receive_stock_configs(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    if not message.text:
        await message.answer(
            "کانفیگ‌ها را به‌صورت متن ارسال کن."
        )
        return

    configs = list(
        dict.fromkeys(
            line.strip()
            for line in message.text.splitlines()
            if line.strip()
        )
    )

    data = await state.get_data()

    added, duplicate = add_configs(
        product_id=data["stock_product_id"],
        configs=configs,
    )

    current_stock = get_stock(
        data["stock_product_id"]
    )

    await state.clear()

    await message.answer(
        "✅ موجودی ثبت شد.\n\n"
        f"➕ اضافه‌شده: {added}\n"
        f"♻️ تکراری: {duplicate}\n"
        f"📦 موجودی فعلی: {current_stock}",
        reply_markup=admin_keyboard,
    )


# =========================================================
# افزودن موجودی تست رایگان
# =========================================================

def trial_settings_keyboard():
    categories = get_all_categories(active_only=True)
    buttons = [[InlineKeyboardButton(text=f"🌐 {category['name']}", callback_data=f"trial_category:{category['id']}")] for category in categories]
    buttons.append([InlineKeyboardButton(text="🚫 غیرفعال‌کردن تست پنلی", callback_data="trial_category:none")])
    buttons.append([InlineKeyboardButton(text="❌ بستن", callback_data="close_message")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def save_trial_settings(category_id: int | None, duration_days: int = 1, volume_gb: float = 1):
    connection = get_db()
    active = 1 if category_id is not None else 0
    connection.execute(
        """
        INSERT INTO trial_settings (id, category_id, duration_days, volume_gb, active, updated_at)
        VALUES (1, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET category_id=excluded.category_id,
            duration_days=excluded.duration_days, volume_gb=excluded.volume_gb,
            active=excluded.active, updated_at=excluded.updated_at
        """,
        (category_id, duration_days, volume_gb, active, now_text()),
    )
    connection.commit()
    connection.close()


@dp.message(F.text == "⚙️ تنظیم تست پنلی")
async def trial_panel_settings_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        "⚙️ دسته‌بندی پنلی تست رایگان را انتخاب کن:",
        reply_markup=trial_settings_keyboard(),
    )


@dp.callback_query(F.data.startswith("trial_category:"))
async def trial_category_callback(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return
    value = callback.data.split(":", 1)[1]
    if value == "none":
        save_trial_settings(None)
        await state.clear()
        await callback.message.answer("✅ تست پنلی غیرفعال شد.", reply_markup=admin_keyboard)
        await callback.answer()
        return
    try:
        category_id = int(value)
    except ValueError:
        await callback.answer("دسته‌بندی معتبر نیست.", show_alert=True)
        return
    if get_category_with_panel(category_id) is None:
        await callback.answer("دسته‌بندی یا پنل فعال نیست.", show_alert=True)
        return
    await state.update_data(trial_category_id=category_id)
    await state.set_state(AdminStates.waiting_trial_days)
    await callback.message.answer("مدت تست را برحسب روز بفرست؛ مثال: 1", reply_markup=cancel_keyboard)
    await callback.answer()


@dp.message(AdminStates.waiting_trial_days)
async def receive_trial_days(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        days = int((message.text or "").strip())
    except ValueError:
        await message.answer("مدت باید عدد صحیح باشد.")
        return
    if days <= 0 or days > 365:
        await message.answer("مدت باید بین 1 تا 365 روز باشد.")
        return
    await state.update_data(trial_days=days)
    await state.set_state(AdminStates.waiting_trial_volume)
    await message.answer("حجم تست را برحسب GB بفرست؛ برای نامحدود 0 بفرست.", reply_markup=cancel_keyboard)


@dp.message(AdminStates.waiting_trial_volume)
async def receive_trial_volume(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        volume = float((message.text or "").strip().replace(",", "."))
    except ValueError:
        await message.answer("حجم باید عدد باشد.")
        return
    if volume < 0 or volume > 10000:
        await message.answer("حجم باید بین 0 تا 10000 GB باشد.")
        return
    data = await state.get_data()
    save_trial_settings(int(data["trial_category_id"]), int(data["trial_days"]), volume)
    await state.clear()
    await message.answer("✅ تست خودکار پنلی تنظیم شد.", reply_markup=admin_keyboard)



async def add_trial_stock_start(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    await state.set_state(
        AdminStates.waiting_trial_configs
    )

    await message.answer(
        "کانفیگ‌های تست رایگان را ارسال کن.\n\n"
        "هر کانفیگ باید در یک خط جدا باشد.",
        reply_markup=cancel_keyboard,
    )


@dp.message(AdminStates.waiting_trial_configs)
async def receive_trial_configs(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    if not message.text:
        await message.answer(
            "کانفیگ‌ها را به‌صورت متن ارسال کن."
        )
        return

    configs = list(
        dict.fromkeys(
            line.strip()
            for line in message.text.splitlines()
            if line.strip()
        )
    )

    added, duplicate = add_trial_configs(configs)

    current_stock = get_trial_stock()

    await state.clear()

    await message.answer(
        "✅ موجودی تست رایگان ثبت شد.\n\n"
        f"➕ اضافه‌شده: {added}\n"
        f"♻️ تکراری: {duplicate}\n"
        f"📦 موجودی فعلی تست: {current_stock}",
        reply_markup=admin_keyboard,
    )


# =========================================================
# بک‌آپ دستی دیتابیس
# =========================================================

@dp.message(F.text == "💾 بک‌آپ دیتابیس")
async def manual_backup_handler(
    message: Message,
):
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "⏳ در حال تهیه بک‌آپ...",
        reply_markup=admin_keyboard,
    )

    await send_backup_to_admins(
        "💾 <b>بک‌آپ دستی دیتابیس</b>\n\n"
        f"🕐 زمان: {now_text()}\n"
        f"👤 درخواست‌شده توسط: "
        f"<code>{message.from_user.id}</code>"
    )


# =========================================================
# مدیریت ادمین‌ها (فقط سوپرادمین‌ها)
# =========================================================

def set_trial_category_keyboard():
    return trial_settings_keyboard()


@dp.message(F.text == "🛡 مدیریت ادمین‌ها")
async def admin_management_start(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    if not is_super_admin(message.from_user.id):
        await message.answer(
            "⛔ فقط سوپرادمین‌ها (ادمین‌های اصلی تنظیم‌شده "
            "در فایل .env) به این بخش دسترسی دارند.",
            reply_markup=admin_keyboard,
        )
        return

    await state.clear()

    admins = get_all_admins()

    text = "🛡 <b>مدیریت ادمین‌ها</b>\n\n"

    for admin in admins:
        icon = "👑" if admin["type"] == "super" else "🛡"
        role = "سوپرادمین" if admin["type"] == "super" else "ادمین"

        text += (
            f"{icon} <code>{admin['telegram_id']}</code> "
            f"({role})\n"
        )

    await message.answer(
        text,
        reply_markup=admin_management_keyboard(),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "admin_add_start")
async def admin_add_start_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_super_admin(callback.from_user.id):
        await callback.answer(
            "فقط سوپرادمین‌ها می‌توانند ادمین اضافه کنند.",
            show_alert=True,
        )
        return

    await state.set_state(
        AdminStates.waiting_new_admin_id
    )

    await callback.message.answer(
        "🆔 آیدی عددی (<code>telegram_id</code>) کاربری "
        "که می‌خواهی ادمین شود را ارسال کن:",
        reply_markup=cancel_keyboard,
        parse_mode="HTML",
    )

    await callback.answer()


@dp.message(AdminStates.waiting_new_admin_id)
async def receive_new_admin_id(
    message: Message,
    state: FSMContext,
):
    if not is_super_admin(message.from_user.id):
        await state.clear()
        return

    value = message.text.strip() if message.text else ""

    if not value.isdigit():
        await message.answer(
            "آیدی باید یک عدد باشد. دوباره ارسال کن."
        )
        return

    new_admin_id = int(value)

    await state.clear()

    if is_admin(new_admin_id):
        await message.answer(
            "این کاربر همین الان هم ادمین است.",
            reply_markup=admin_keyboard,
        )
        return

    added = add_admin(
        telegram_id=new_admin_id,
        added_by=message.from_user.id,
    )

    if not added:
        await message.answer(
            "❌ خطا در افزودن ادمین.",
            reply_markup=admin_keyboard,
        )
        return

    await message.answer(
        f"✅ کاربر <code>{new_admin_id}</code> به عنوان "
        "ادمین اضافه شد.",
        reply_markup=admin_keyboard,
        parse_mode="HTML",
    )

    try:
        await bot.send_message(
            new_admin_id,
            "🎉 شما به عنوان ادمین ربات اضافه شدید.\n\n"
            "برای دسترسی به پنل مدیریت، دستور /admin را ارسال کن.",
        )
    except Exception as error:
        print(
            "خطا در اطلاع‌رسانی ادمین جدید:",
            error,
        )


@dp.callback_query(F.data == "admin_remove_start")
async def admin_remove_start_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_super_admin(callback.from_user.id):
        await callback.answer(
            "فقط سوپرادمین‌ها می‌توانند ادمین حذف کنند.",
            show_alert=True,
        )
        return

    await state.set_state(
        AdminStates.waiting_remove_admin_id
    )

    await callback.message.answer(
        "🆔 آیدی عددی ادمینی که می‌خواهی حذف کنی را ارسال کن.\n\n"
        "توجه: سوپرادمین‌های تنظیم‌شده در .env از این طریق "
        "قابل حذف نیستند.",
        reply_markup=cancel_keyboard,
        parse_mode="HTML",
    )

    await callback.answer()


@dp.message(AdminStates.waiting_remove_admin_id)
async def receive_remove_admin_id(
    message: Message,
    state: FSMContext,
):
    if not is_super_admin(message.from_user.id):
        await state.clear()
        return

    value = message.text.strip() if message.text else ""

    if not value.isdigit():
        await message.answer(
            "آیدی باید یک عدد باشد. دوباره ارسال کن."
        )
        return

    target_id = int(value)

    await state.clear()

    if target_id in ADMIN_IDS:
        await message.answer(
            "⛔ این کاربر سوپرادمین است و از طریق ربات "
            "قابل حذف نیست. برای حذف باید از فایل .env "
            "اقدام کنی.",
            reply_markup=admin_keyboard,
        )
        return

    removed = remove_admin(target_id)

    if not removed:
        await message.answer(
            "این کاربر در لیست ادمین‌های اضافه‌شده نبود.",
            reply_markup=admin_keyboard,
        )
        return

    await message.answer(
        f"✅ دسترسی ادمین کاربر "
        f"<code>{target_id}</code> حذف شد.",
        reply_markup=admin_keyboard,
        parse_mode="HTML",
    )

    try:
        await bot.send_message(
            target_id,
            "⛔ دسترسی ادمین شما در ربات حذف شد.",
        )
    except Exception:
        pass


@dp.message(F.text == "🌐 مدیریت پنل‌های VPN")
async def xui_management_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        "🌐 <b>مدیریت پنل‌ها و دسته‌بندی‌های VPN</b>",
        reply_markup=panel_management_keyboard(),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "xui_management")
async def xui_management_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return
    await callback.message.edit_text("🌐 <b>مدیریت پنل‌ها و دسته‌بندی‌های VPN</b>", reply_markup=panel_management_keyboard(), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "xui_panels")
async def xui_panels_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return
    await callback.message.answer(
        f"🌐 <b>پنل‌های VPN</b>\n\n"
        "برای مشاهده وضعیت آنلاین، روی نام هر پنل بزن:",
        reply_markup=xui_panels_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "xui_categories")
async def xui_categories_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return
    await callback.message.edit_text("🗂 <b>دسته‌بندی‌ها</b>", reply_markup=xui_categories_keyboard(), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "xui_panel_add")
async def xui_panel_add_callback(callback: CallbackQuery, state: FSMContext):
    if not is_super_admin(callback.from_user.id):
        await callback.answer("فقط سوپرادمین مجاز است.", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_panel_name)
    await callback.message.answer("نام پنل را ارسال کن:", reply_markup=cancel_keyboard)
    await callback.answer()


@dp.message(AdminStates.waiting_panel_name)
async def receive_panel_name(message: Message, state: FSMContext):
    if not is_super_admin(message.from_user.id):
        return
    name = (message.text or "").strip()
    if not name:
        await message.answer("نام پنل خالی است.")
        return
    await state.update_data(panel_name=name)
    await state.set_state(AdminStates.waiting_panel_url)
    await message.answer("آدرس کامل پنل را ارسال کن؛ مثال: https://vpn.example.com", reply_markup=cancel_keyboard)


@dp.message(AdminStates.waiting_panel_url)
async def receive_panel_url(message: Message, state: FSMContext):
    url = normalize_xui_base_url(message.text or "")
    if not url.startswith(("http://", "https://")):
        await message.answer("آدرس باید با http:// یا https:// شروع شود.")
        return
    await state.update_data(panel_url=url)
    await state.set_state(AdminStates.waiting_panel_subscription_url)
    await message.answer(
        "لینک Subscription نمونه همین پنل را ارسال کن تا برای هر کاربر لینک اشتراک ساخته شود.\n"
        "مثال: https://domain:2096/sub/OLD_TOKEN\n\n"
        "اگر پنل لینک Subscription ندارد، «ندارم» را ارسال کن.",
        reply_markup=cancel_keyboard,
    )


@dp.message(AdminStates.waiting_panel_subscription_url)
async def receive_panel_subscription_url(message: Message, state: FSMContext):
    value = (message.text or "").strip()
    if value.lower() in {"ندارم", "نداره", "none", "no"}:
        await message.answer(
            "برای محصولات پنلی باید لینک Subscription نمونه وارد شود؛ "
            "مثال: https://sub.example.com:2096/sub/OLD_TOKEN"
        )
        return
    if not value.startswith(("http://", "https://")):
        await message.answer("لینک باید با http:// یا https:// شروع شود.")
        return
    await state.update_data(panel_subscription_url=value)
    await state.set_state(AdminStates.waiting_panel_token)
    await message.answer("API Token پنل را ارسال کن. این پیام بعد از دریافت حذف می‌شود.", reply_markup=cancel_keyboard)


@dp.message(AdminStates.waiting_panel_token)
async def receive_panel_token(message: Message, state: FSMContext):
    token = (message.text or "").strip()
    data = await state.get_data()
    if not token or len(token) < 8:
        await message.answer("API Token معتبر نیست.")
        return
    try:
        await message.delete()
    except Exception:
        pass
    await message.answer("⏳ توکن دریافت شد؛ در حال تست اتصال و ثبت پنل...")
    try:
        inbounds = await XUIClient({"base_url": data["panel_url"], "api_token": token}).list_inbounds()
    except XUIError as error:
        await message.answer(f"❌ تست اتصال پنل ناموفق بود: {error}")
        return
    panel_id = create_xui_panel(
        data["panel_name"], data["panel_url"], token,
        data.get("panel_subscription_url"),
    )
    await state.clear()
    if panel_id is None:
        await message.answer("❌ پنلی با این نام قبلاً ثبت شده است.", reply_markup=admin_keyboard)
        return
    await message.answer(
        "✅ پنل با موفقیت ثبت و تست شد.\n"
        f"📋 تعداد inboundهای قابل استفاده: {len(inbounds)}",
        reply_markup=admin_keyboard,
    )


@dp.callback_query(F.data == "xui_category_add")
async def xui_category_add_callback(callback: CallbackQuery, state: FSMContext):
    if not is_super_admin(callback.from_user.id):
        await callback.answer("فقط سوپرادمین مجاز است.", show_alert=True)
        return
    if not get_all_xui_panels(active_only=True):
        await callback.answer("ابتدا یک پنل ثبت کن.", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_category_name)
    await callback.message.answer("نام دسته‌بندی را ارسال کن؛ مثال: VIP ایران", reply_markup=cancel_keyboard)
    await callback.answer()


@dp.message(AdminStates.waiting_category_name)
async def receive_category_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        await message.answer("نام دسته‌بندی خالی است.")
        return
    await state.update_data(category_name=name)
    await state.set_state(AdminStates.waiting_category_panel)
    await message.answer("پنل این دسته‌بندی را انتخاب کن:", reply_markup=xui_panel_select_keyboard())


@dp.callback_query(F.data.startswith("xui_category_panel:"))
async def xui_category_panel_callback(callback: CallbackQuery, state: FSMContext):
    panel_id = int(callback.data.split(":")[1])
    panel = get_xui_panel(panel_id)
    if panel is None:
        await callback.answer("پنل پیدا نشد.", show_alert=True)
        return
    try:
        inbounds = await XUIClient(panel).list_inbounds()
    except XUIError as error:
        await callback.answer(str(error), show_alert=True)
        return
    await state.update_data(category_panel_id=panel_id, category_inbounds=inbounds, selected_inbounds=[])
    await state.set_state(AdminStates.waiting_category_inbounds)
    await callback.message.answer("یک یا چند inbound را انتخاب کن:", reply_markup=xui_inbounds_keyboard(inbounds))
    await callback.answer()


@dp.callback_query(AdminStates.waiting_category_inbounds, F.data.startswith("xui_inbound_toggle:"))
async def xui_inbound_toggle_callback(callback: CallbackQuery, state: FSMContext):
    inbound_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    selected = list(data.get("selected_inbounds", []))
    if inbound_id in selected:
        selected.remove(inbound_id)
    else:
        selected.append(inbound_id)
    await state.update_data(selected_inbounds=selected)
    await callback.message.edit_reply_markup(reply_markup=xui_inbounds_keyboard(data.get("category_inbounds", []), selected))
    await callback.answer()


@dp.callback_query(AdminStates.waiting_category_inbounds, F.data == "xui_category_save")
async def xui_category_save_callback(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_inbounds", [])
    if not selected:
        await callback.answer("حداقل یک inbound انتخاب کن.", show_alert=True)
        return
    category_id = create_category(data["category_name"], data["category_panel_id"], selected)
    await state.clear()
    if category_id is None:
        await callback.message.answer("❌ دسته‌بندی با این نام قبلاً ثبت شده است.", reply_markup=admin_keyboard)
    else:
        await callback.message.answer(f"✅ دسته‌بندی با شناسه {category_id} ساخته شد.", reply_markup=admin_keyboard)
    await callback.answer()




@dp.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    await callback.answer()


@dp.callback_query(F.data.startswith("xui_category_delete:"))
async def xui_category_delete_callback(callback: CallbackQuery):
    if not is_super_admin(callback.from_user.id):
        await callback.answer("فقط سوپرادمین مجاز است.", show_alert=True)
        return
    category_id = int(callback.data.split(":")[1])
    category = get_category(category_id)
    if category is None:
        await callback.answer("دسته‌بندی پیدا نشد.", show_alert=True)
        return
    await callback.message.edit_text(
        f"⚠️ آیا دسته‌بندی «{html.escape(category['name'])}» حذف شود؟\n\n"
        "اتصال این دسته‌بندی به inboundها نیز حذف می‌شود؛ خود inboundهای پنل حذف نمی‌شوند.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ بله، حذف شود", callback_data=f"xui_category_delete_confirm:{category_id}")],
            [InlineKeyboardButton(text="❌ لغو", callback_data="xui_categories")],
        ]),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("xui_category_delete_confirm:"))
async def xui_category_delete_confirm_callback(callback: CallbackQuery):
    if not is_super_admin(callback.from_user.id):
        await callback.answer("فقط سوپرادمین مجاز است.", show_alert=True)
        return
    category_id = int(callback.data.split(":")[1])
    deleted, result = delete_category(category_id)
    if not deleted:
        await callback.answer(result, show_alert=True)
        return
    await callback.message.edit_text(result, reply_markup=xui_categories_keyboard())
    await callback.answer("دسته‌بندی حذف شد.")


@dp.callback_query(F.data.startswith("xui_panel_view:"))
async def xui_panel_view_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return
    panel_id = int(callback.data.split(":")[1])
    panel = get_xui_panel(panel_id)
    if panel is None:
        await callback.answer("پنل پیدا نشد.", show_alert=True)
        return
    try:
        server_status = await XUIClient(panel).get_server_status()
        status_text = "✅ <b>وضعیت اتصال: آنلاین</b>\n" + format_server_status(server_status)
    except XUIError as error:
        status_text = f"❌ <b>وضعیت اتصال: آفلاین/خطادار</b>\n{html.escape(str(error))}"
    try:
        inbounds = await XUIClient(panel).list_inbounds()
        inbound_text = "\n".join(f"• {row['id']} — {row['remark']} ({row['protocol']}:{row['port']})" for row in inbounds)
        text = f"🌐 <b>{html.escape(panel['name'])}</b>\n\n{status_text}\n\n📡 Inboundها:\n{inbound_text or '—'}"
    except XUIError as error:
        text = f"🌐 <b>{html.escape(panel['name'])}</b>\n\n{status_text}\n\n❌ Inboundها دریافت نشد: {html.escape(str(error))}"
    await callback.message.edit_text(
        text + "\n\n🔗 لینک Sub نمونه: " + ("ثبت شده ✅" if panel["subscription_url"] else "ثبت نشده ❌"),
        reply_markup=xui_panel_options_keyboard(panel_id),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("xui_panel_delete:"))
async def xui_panel_delete_callback(callback: CallbackQuery):
    if not is_super_admin(callback.from_user.id):
        await callback.answer("فقط سوپرادمین مجاز است.", show_alert=True)
        return
    panel_id = int(callback.data.split(":")[1])
    panel = get_xui_panel(panel_id)
    if panel is None:
        await callback.answer("پنل پیدا نشد.", show_alert=True)
        return
    await callback.message.edit_text(
        f"⚠️ آیا از حذف پنل «{html.escape(panel['name'])}» مطمئنی؟\n\n"
        "این کار اطلاعات پنل را از ربات حذف می‌کند؛ خود سرور و کلاینت‌های داخل آن حذف نمی‌شوند.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ بله، حذف شود", callback_data=f"xui_panel_delete_confirm:{panel_id}")],
            [InlineKeyboardButton(text="❌ لغو", callback_data="xui_panels")],
        ]),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("xui_panel_delete_confirm:"))
async def xui_panel_delete_confirm_callback(callback: CallbackQuery):
    if not is_super_admin(callback.from_user.id):
        await callback.answer("فقط سوپرادمین مجاز است.", show_alert=True)
        return
    panel_id = int(callback.data.split(":")[1])
    deleted, result = delete_xui_panel(panel_id)
    if not deleted:
        await callback.answer(result, show_alert=True)
        return
    await callback.message.edit_text(result, reply_markup=xui_panels_keyboard())
    await callback.answer("پنل حذف شد.")


@dp.callback_query(F.data.startswith("xui_panel_suburl:"))
async def xui_panel_suburl_callback(callback: CallbackQuery, state: FSMContext):
    if not is_super_admin(callback.from_user.id):
        await callback.answer("فقط سوپرادمین مجاز است.", show_alert=True)
        return
    panel_id = int(callback.data.split(":")[1])
    await state.update_data(subscription_panel_id=panel_id)
    await state.set_state(AdminStates.waiting_panel_subscription_update)
    await callback.message.answer(
        "لینک Subscription نمونه جدید را ارسال کن؛ مثال:\n"
        "https://sub.example.com:2096/sub/OLD_TOKEN\n"
        "یا قالب https://domain/sub/{sub_id}",
        reply_markup=cancel_keyboard,
    )
    await callback.answer()


@dp.message(AdminStates.waiting_panel_subscription_update)
async def receive_panel_subscription_update(message: Message, state: FSMContext):
    value = (message.text or "").strip()
    if not value.startswith(("http://", "https://")):
        await message.answer("لینک باید با http:// یا https:// شروع شود.")
        return
    data = await state.get_data()
    update_xui_panel_subscription_url(int(data["subscription_panel_id"]), value)
    await state.clear()
    await message.answer("✅ لینک Subscription پنل به‌روزرسانی شد.", reply_markup=admin_keyboard)


@dp.callback_query(F.data.startswith("xui_category_view:"))
async def xui_category_view_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return
    category_id = int(callback.data.split(":")[1])
    category = get_category_with_panel(category_id)
    if category is None:
        await callback.answer("دسته‌بندی پیدا نشد.", show_alert=True)
        return
    inbound_ids = category_inbound_ids(category)
    await callback.message.answer(
        f"🗂 <b>{html.escape(category['name'])}</b>\n"
        f"🌐 پنل: {html.escape(category['panel_name'] or '—')}\n"
        f"📡 Inboundها: {', '.join(map(str, inbound_ids)) or '—'}",
        parse_mode="HTML",
    )
    await callback.answer()



async def tutorial_admin_start(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    await state.clear()

    await message.answer(
        "🎬 <b>مدیریت آموزش اتصال</b>\n\n"
        "سیستم‌عامل موردنظر را انتخاب کن.\n"
        "✅ یعنی ویدیو ثبت شده، ⭕️ یعنی هنوز ثبت نشده:",
        reply_markup=admin_tutorial_os_keyboard(),
        parse_mode="HTML",
    )


@dp.callback_query(F.data.startswith("admin_tut_os:"))
async def admin_tutorial_os_callback(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "دسترسی ندارید.",
            show_alert=True,
        )
        return

    os_key = callback.data.split(":")[1]

    os_data = TUTORIAL_STRUCTURE.get(os_key)

    if os_data is None:
        await callback.answer(
            "سیستم‌عامل پیدا نشد.",
            show_alert=True,
        )
        return

    try:
        await callback.message.edit_text(
            f"🎬 <b>{os_data['label']}</b>\n\n"
            "کلاینتی که می‌خواهی ویدیویش را ثبت/تغییر دهی "
            "را انتخاب کن:",
            reply_markup=admin_tutorial_client_keyboard(os_key),
            parse_mode="HTML",
        )
    except Exception:
        pass

    await callback.answer()


@dp.callback_query(F.data == "admin_tut_back_os")
async def admin_tutorial_back_os_callback(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "دسترسی ندارید.",
            show_alert=True,
        )
        return

    try:
        await callback.message.edit_text(
            "🎬 <b>مدیریت آموزش اتصال</b>\n\n"
            "سیستم‌عامل موردنظر را انتخاب کن.\n"
            "✅ یعنی ویدیو ثبت شده، ⭕️ یعنی هنوز ثبت نشده:",
            reply_markup=admin_tutorial_os_keyboard(),
            parse_mode="HTML",
        )
    except Exception:
        pass

    await callback.answer()


@dp.callback_query(F.data.startswith("admin_tut_client:"))
async def admin_tutorial_client_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "دسترسی ندارید.",
            show_alert=True,
        )
        return

    _, os_key, client_key = callback.data.split(":")

    os_data = TUTORIAL_STRUCTURE.get(os_key)

    if os_data is None or client_key not in os_data["clients"]:
        await callback.answer(
            "کلاینت پیدا نشد.",
            show_alert=True,
        )
        return

    client_label = os_data["clients"][client_key]

    await state.update_data(
        tutorial_os_key=os_key,
        tutorial_client_key=client_key,
    )

    await state.set_state(
        AdminStates.waiting_tutorial_video
    )

    existing = get_tutorial_video(os_key, client_key)

    status_text = (
        "🔁 در حال حاضر یک ویدیو برای این کلاینت ثبت شده "
        "و با ثبت لینک جدید جایگزین می‌شود.\n\n"
        if existing
        else ""
    )

    await callback.message.answer(
        f"🎬 <b>{os_data['label']} - {client_label}</b>\n\n"
        f"{status_text}"
        "ابتدا ویدیوی آموزشی را در کانال آپلود کن، سپس "
        "لینک همان پست را اینجا ارسال کن.\n\n"
        "مثال لینک:\n"
        "<code>https://t.me/mychannel/123</code>",
        reply_markup=cancel_keyboard,
        parse_mode="HTML",
    )

    await callback.answer()


@dp.message(AdminStates.waiting_tutorial_video)
async def receive_tutorial_video_link(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    if message.text == "❌ لغو":
        return

    if not message.text:
        await message.answer(
            "لطفاً لینک پست ویدیو در کانال را به‌صورت متن ارسال کن."
        )
        return

    data = await state.get_data()

    os_key = data.get("tutorial_os_key")
    client_key = data.get("tutorial_client_key")

    if not os_key or not client_key:
        await state.clear()

        await message.answer(
            "خطا: اطلاعات کلاینت پیدا نشد. دوباره تلاش کن.",
            reply_markup=admin_keyboard,
        )
        return

    parsed = parse_telegram_post_link(message.text)

    if parsed is None:
        await message.answer(
            "❌ لینک معتبر نیست.\n\n"
            "لینک باید شبیه یکی از این‌ها باشد:\n"
            "<code>https://t.me/mychannel/123</code>\n"
            "<code>https://t.me/c/1234567890/123</code>\n\n"
            "دوباره ارسال کن یا «❌ لغو» بزن.",
            parse_mode="HTML",
        )
        return

    chat_id, video_message_id = parsed

    # اعتبارسنجی: بررسی می‌کنیم ربات واقعاً به این پیام دسترسی دارد
    try:
        test_copy = await bot.copy_message(
            chat_id=message.from_user.id,
            from_chat_id=chat_id,
            message_id=video_message_id,
        )
    except Exception as error:
        print(
            "خطا در اعتبارسنجی لینک ویدیوی آموزشی:",
            error,
        )

        await message.answer(
            "❌ ربات نتوانست این پیام را از کانال بخواند.\n\n"
            "مطمئن شو:\n"
            "• ربات عضو (و ترجیحاً ادمین) کانال است\n"
            "• لینک درست کپی شده و پست حذف نشده است\n\n"
            "دوباره تلاش کن یا «❌ لغو» بزن."
        )
        return

    set_tutorial_video(
        os_key=os_key,
        client_key=client_key,
        chat_id=chat_id,
        message_id=video_message_id,
    )

    await state.clear()

    os_data = TUTORIAL_STRUCTURE[os_key]
    client_label = os_data["clients"][client_key]

    await message.answer(
        f"✅ ویدیوی آموزش «{os_data['label']} - "
        f"{client_label}» ثبت شد.\n\n"
        "پیام بالا برای تست به‌صورت پیش‌نمایش برایت ارسال شد.",
        reply_markup=admin_keyboard,
    )


@dp.message(F.text == "📊 گزارش محصولات")
async def products_report(
    message: Message,
):
    if not is_admin(message.from_user.id):
        return

    products = get_products()

    if not products:
        await message.answer(
            "محصولی ثبت نشده است.",
            reply_markup=admin_keyboard,
        )
        return

    text = "📊 <b>گزارش محصولات</b>\n\n"

    for product in products:
        text += (
            f"🆔 شناسه: <code>{product['id']}</code>\n"
            f"🛍 نام: <b>{html.escape(product['name'])}</b>\n"
            f"⏳ مدت: {product['duration_days']} روز\n"
            f"📊 حجم: {product['volume_gb']} GB\n"
            f"💰 قیمت: {product['price']:,.0f} تومان\n"
            f"📦 موجودی: "
            f"<b>{'∞ (پنلی)' if product['category_id'] else get_stock(product['id'])}</b>\n"
        )

    text += (
        "🎁 <b>موجودی تست رایگان:</b> "
        f"{get_trial_stock()}\n"
    )

    await message.answer(
        text,
        reply_markup=admin_keyboard,
        parse_mode="HTML",
    )


@dp.message(F.text == "👥 مدیریت کاربران")
async def user_management_start(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    await state.clear()

    keyboard, total = users_list_keyboard(page=0)

    if total == 0:
        await message.answer(
            "هنوز کاربری ثبت نشده است.",
            reply_markup=admin_keyboard,
        )
        return

    await message.answer(
        f"👥 <b>مدیریت کاربران</b>\n\n"
        f"تعداد کاربران ثبت‌شده: <b>{total}</b>\n\n"
        "روی هر کاربر بزن تا اطلاعات و گزینه‌های "
        "مدیریتش باز شود:",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


def build_user_card_text(telegram_id: int):
    user = get_user(telegram_id)

    if user is None:
        return None

    username_text = (
        "@" + html.escape(user["username"])
        if user["username"]
        else "بدون یوزرنیم"
    )

    order_count = get_user_order_count(telegram_id)
    trial_used = has_claimed_trial(telegram_id)

    return (
        "👤 <b>اطلاعات کاربر</b>\n\n"
        f"🆔 آیدی: <code>{user['telegram_id']}</code>\n"
        f"👤 نام: "
        f"{html.escape(user['first_name'] or '')}\n"
        f"🔗 یوزرنیم: {username_text}\n"
        f"👛 موجودی کیف پول: "
        f"<b>{float(user['balance']):,.0f}</b> تومان\n"
        f"🧾 تعداد سفارش‌ها: {order_count}\n"
        f"🎁 تست رایگان: "
        f"{'استفاده شده' if trial_used else 'استفاده نشده'}\n"
        f"📅 عضویت: {user['created_at']}"
    )


async def show_user_card(message: Message, telegram_id: int, page: int = 0):
    text = build_user_card_text(telegram_id)

    if text is None:
        await message.answer(
            "کاربری با این آیدی پیدا نشد.",
            reply_markup=admin_keyboard,
        )
        return

    await message.answer(
        text,
        reply_markup=user_management_keyboard(telegram_id, page),
        parse_mode="HTML",
    )


@dp.callback_query(F.data.startswith("users_list:"))
async def users_list_callback(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "دسترسی ندارید.",
            show_alert=True,
        )
        return

    page = int(callback.data.split(":")[1])

    keyboard, total = users_list_keyboard(page=page)

    try:
        await callback.message.edit_text(
            f"👥 <b>مدیریت کاربران</b>\n\n"
            f"تعداد کاربران ثبت‌شده: <b>{total}</b>\n\n"
            "روی هر کاربر بزن تا اطلاعات و گزینه‌های "
            "مدیریتش باز شود:",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    except Exception:
        pass

    await callback.answer()


@dp.callback_query(F.data.startswith("user_view:"))
async def user_view_callback(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "دسترسی ندارید.",
            show_alert=True,
        )
        return

    _, telegram_id_str, page_str = callback.data.split(":")

    telegram_id = int(telegram_id_str)
    page = int(page_str)

    text = build_user_card_text(telegram_id)

    if text is None:
        await callback.answer(
            "کاربری با این آیدی پیدا نشد.",
            show_alert=True,
        )
        return

    try:
        await callback.message.edit_text(
            text,
            reply_markup=user_management_keyboard(
                telegram_id, page
            ),
            parse_mode="HTML",
        )
    except Exception:
        pass

    await callback.answer()


@dp.callback_query(F.data == "users_search")
async def users_search_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "دسترسی ندارید.",
            show_alert=True,
        )
        return

    await state.set_state(
        AdminStates.waiting_user_search
    )

    await callback.message.answer(
        "آیدی عددی (<code>telegram_id</code>) کاربر "
        "موردنظر را ارسال کن:",
        reply_markup=cancel_keyboard,
        parse_mode="HTML",
    )

    await callback.answer()


@dp.message(AdminStates.waiting_user_search)
async def receive_user_search(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    value = message.text.strip() if message.text else ""

    if not value.isdigit():
        await message.answer(
            "آیدی باید یک عدد باشد. دوباره ارسال کن."
        )
        return

    await state.clear()

    await show_user_card(message, int(value))


# =========================================================
# دکمه‌های مدیریت یک کاربر (کیف پول / ریست تست)
# =========================================================

@dp.callback_query(F.data.startswith("balance_add:"))
async def balance_add_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "دسترسی ندارید.",
            show_alert=True,
        )
        return

    telegram_id = int(callback.data.split(":")[1])

    await state.update_data(
        balance_target_id=telegram_id,
        balance_mode="add",
    )

    await state.set_state(
        AdminStates.waiting_balance_amount
    )

    await callback.message.answer(
        f"مبلغی که می‌خواهی به کیف پول کاربر "
        f"<code>{telegram_id}</code> اضافه شود را "
        "به تومان ارسال کن:",
        reply_markup=cancel_keyboard,
        parse_mode="HTML",
    )

    await callback.answer()


@dp.callback_query(F.data.startswith("balance_sub:"))
async def balance_sub_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "دسترسی ندارید.",
            show_alert=True,
        )
        return

    telegram_id = int(callback.data.split(":")[1])

    await state.update_data(
        balance_target_id=telegram_id,
        balance_mode="sub",
    )

    await state.set_state(
        AdminStates.waiting_balance_amount
    )

    await callback.message.answer(
        f"مبلغی که می‌خواهی از کیف پول کاربر "
        f"<code>{telegram_id}</code> کم شود را "
        "به تومان ارسال کن:",
        reply_markup=cancel_keyboard,
        parse_mode="HTML",
    )

    await callback.answer()


@dp.message(AdminStates.waiting_balance_amount)
async def receive_balance_amount(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    value = (
        message.text.strip().replace(",", "")
        if message.text
        else ""
    )

    try:
        amount = Decimal(value)
    except InvalidOperation:
        await message.answer(
            "مبلغ واردشده معتبر نیست."
        )
        return

    if amount <= 0:
        await message.answer(
            "مبلغ باید بیشتر از صفر باشد."
        )
        return

    data = await state.get_data()

    telegram_id = data["balance_target_id"]
    mode = data["balance_mode"]

    signed_amount = (
        float(amount)
        if mode == "add"
        else -float(amount)
    )

    try:
        result = adjust_balance(
            telegram_id=telegram_id,
            amount=signed_amount,
            tx_type=(
                "admin_credit"
                if mode == "add"
                else "admin_debit"
            ),
            admin_id=message.from_user.id,
            note="تنظیم دستی توسط ادمین",
        )

    except Exception as error:
        print(
            "خطا هنگام تغییر موجودی کاربر:",
            error,
        )

        await state.clear()

        await message.answer(
            "خطایی رخ داد.",
            reply_markup=admin_keyboard,
        )
        return

    await state.clear()

    if not result["success"]:
        await message.answer(
            f"❌ {result['message']}",
            reply_markup=admin_keyboard,
        )
        return

    action_text = (
        "افزایش یافت" if mode == "add" else "کاهش یافت"
    )

    await message.answer(
        f"✅ موجودی کیف پول کاربر "
        f"<code>{telegram_id}</code> {action_text}.\n\n"
        f"👛 موجودی جدید: "
        f"<b>{result['new_balance']:,.0f}</b> تومان",
        reply_markup=admin_keyboard,
        parse_mode="HTML",
    )


@dp.callback_query(F.data.startswith("reset_trial:"))
async def reset_trial_callback(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "دسترسی ندارید.",
            show_alert=True,
        )
        return

    telegram_id = int(callback.data.split(":")[1])

    connection = get_db()

    cursor = connection.execute(
        """
        DELETE FROM trial_claims
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )

    connection.commit()
    connection.close()

    if cursor.rowcount == 0:
        await callback.answer(
            "این کاربر تست رایگان استفاده نکرده بود.",
            show_alert=True,
        )
        return

    await callback.message.answer(
        f"♻️ اکانت تست کاربر "
        f"<code>{telegram_id}</code> ریست شد.\n"
        "این کاربر می‌تواند دوباره تست رایگان دریافت کند.",
        parse_mode="HTML",
    )

    await callback.answer(
        "ریست شد."
    )


# =========================================================
# پیام همگانی
# =========================================================

@dp.message(F.text == "📢 پیام همگانی")
async def broadcast_start(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    await state.set_state(
        AdminStates.waiting_broadcast_message
    )

    await message.answer(
        "📢 پیامی که می‌خواهی برای همه کاربران ارسال شود "
        "را بفرست.\n\n"
        "می‌تواند متن، عکس یا هر نوع پیام دیگری باشد.",
        reply_markup=cancel_keyboard,
    )


@dp.message(AdminStates.waiting_broadcast_message)
async def receive_broadcast_message(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    if message.text == "❌ لغو":
        await state.clear()

        await message.answer(
            "ارسال پیام همگانی لغو شد.",
            reply_markup=admin_keyboard,
        )
        return

    await state.clear()

    users = get_users()

    await message.answer(
        f"⏳ در حال ارسال پیام برای "
        f"{len(users)} کاربر...",
        reply_markup=admin_keyboard,
    )

    sent = 0
    failed = 0

    for user in users:
        try:
            await message.copy_to(
                chat_id=user["telegram_id"]
            )
            sent += 1

        except Exception:
            failed += 1

        await asyncio.sleep(0.05)

    await message.answer(
        "📢 <b>نتیجه ارسال پیام همگانی</b>\n\n"
        f"✅ موفق: {sent}\n"
        f"❌ ناموفق: {failed}",
        reply_markup=admin_keyboard,
        parse_mode="HTML",
    )


# =========================================================
# خرید اشتراک توسط کاربر
# =========================================================

@dp.message(F.text == "🛒 خرید اشتراک")
async def buy_start(
    message: Message,
):
    save_user(message.from_user)

    products = get_products()

    if not products:
        await message.answer(
            "در حال حاضر محصولی برای فروش وجود ندارد.",
            reply_markup=get_main_keyboard(),
        )
        return

    await message.answer(
        "🛒 محصول موردنظر را انتخاب کن:",
        reply_markup=products_keyboard(),
    )


@dp.callback_query(F.data.startswith("buy:"))
async def buy_product_callback(
    callback: CallbackQuery,
):
    save_user(callback.from_user)

    product_id = int(
        callback.data.split(":")[1]
    )

    product = get_product(product_id)

    if product is None:
        await callback.answer(
            "محصول پیدا نشد.",
            show_alert=True,
        )
        return

    if product["category_id"] is None and get_stock(product_id) <= 0:
        await callback.answer(
            "موجودی این محصول تمام شده است.",
            show_alert=True,
        )
        return

    order, error = create_order(
        telegram_id=callback.from_user.id,
        product_id=product_id,
    )

    if error:
        await callback.answer(
            error,
            show_alert=True,
        )
        return

    user = get_user(callback.from_user.id)
    balance = float(user["balance"]) if user else 0.0

    await callback.message.answer(
        "🛍 <b>روش پرداخت را انتخاب کن</b>\n\n"
        f"📦 محصول: "
        f"<b>{html.escape(product['name'])}</b>\n"
        f"⏳ مدت: "
        f"<b>{product['duration_days']}</b> روز\n"
        f"📊 حجم: "
        f"<b>{product['volume_gb']} GB</b>\n"
        f"💰 مبلغ قابل پرداخت: "
        f"<b>{product['price']:,.0f}</b> تومان\n\n"
        f"👛 موجودی کیف پول شما: "
        f"<b>{balance:,.0f}</b> تومان",
        reply_markup=buy_payment_method_keyboard(
            order["id"]
        ),
        parse_mode="HTML",
    )

    await callback.answer()


@dp.callback_query(F.data.startswith("pay_card:"))
async def pay_card_callback(
    callback: CallbackQuery,
):
    order_id = int(
        callback.data.split(":")[1]
    )

    order = get_order(order_id)

    if order is None:
        await callback.answer(
            "سفارش پیدا نشد.",
            show_alert=True,
        )
        return

    if order["telegram_id"] != callback.from_user.id:
        await callback.answer(
            "این سفارش متعلق به شما نیست.",
            show_alert=True,
        )
        return

    if order["status"] != "pending_payment":
        await callback.answer(
            "این سفارش قبلاً پردازش شده است.",
            show_alert=True,
        )
        return

    await callback.message.answer(
        "💳 <b>پرداخت کارت‌به‌کارت</b>\n\n"
        f"📦 محصول: "
        f"<b>{html.escape(order['product_name'])}</b>\n"
        f"⏳ مدت: "
        f"<b>{order['duration_days']}</b> روز\n"
        f"📊 حجم: "
        f"<b>{order['volume_gb']} GB</b>\n"
        f"💰 مبلغ قابل پرداخت: "
        f"<b>{order['price']:,.0f}</b> تومان\n\n"
        "لطفاً مبلغ دقیق را به شماره کارت زیر "
        "کارت‌به‌کارت کن:\n\n"
        f"💳 شماره کارت:\n"
        f"<code>{html.escape(CARD_NUMBER)}</code>\n\n"
        f"👤 به نام: "
        f"<b>{html.escape(CARD_OWNER)}</b>\n\n"
        "بعد از انجام کارت‌به‌کارت، روی دکمه "
        "«ارسال رسید پرداخت» بزن و عکس رسید را ارسال کن.\n\n"
        f"⏱ اگر ادمین تا {AUTO_APPROVE_MINUTES} دقیقه "
        "رسید را بررسی نکند، سفارش خودکار تأیید می‌شود.",
        reply_markup=payment_keyboard(
            order["id"]
        ),
        parse_mode="HTML",
    )

    await callback.answer()


@dp.callback_query(F.data.startswith("pay_wallet:"))
async def pay_wallet_callback(
    callback: CallbackQuery,
):
    order_id = int(
        callback.data.split(":")[1]
    )

    order = get_order(order_id)

    if order is None:
        await callback.answer(
            "سفارش پیدا نشد.",
            show_alert=True,
        )
        return

    if order["telegram_id"] != callback.from_user.id:
        await callback.answer(
            "این سفارش متعلق به شما نیست.",
            show_alert=True,
        )
        return

    if order["status"] != "pending_payment":
        await callback.answer(
            "این سفارش قبلاً پردازش شده است.",
            show_alert=True,
        )
        return

    if order["category_id"] is not None:
        try:
            result = await pay_xui_order_with_wallet(order_id)
        except XUIError as error:
            await callback.answer(str(error), show_alert=True)
            return
        except Exception as error:
            print("خطا در پرداخت پنلی:", error)
            await callback.answer("ساخت اشتراک در پنل ناموفق بود؛ مبلغ برگشت داده شد.", show_alert=True)
            return
        if not result or not result.get("success"):
            await callback.answer((result or {}).get("message", "پرداخت انجام نشد."), show_alert=True)
            return
        await send_product_to_user(result)
        await callback.answer("✅ اشتراک ساخته و تحویل شد.")
        return

    try:
        result = pay_order_with_wallet(
            order_id=order_id,
        )
    except Exception as error:
        print("خطا در پرداخت با کیف پول:", error)
        await callback.answer("خطایی رخ داد. دوباره تلاش کن.", show_alert=True)
        return

    if not result["success"]:
        await callback.answer(
            result["message"],
            show_alert=True,
        )
        return

    try:
        await callback.message.edit_reply_markup(
            reply_markup=None
        )
    except Exception:
        pass

    await send_product_to_user(result)

    await callback.answer(
        "✅ پرداخت با موفقیت از کیف پول انجام شد."
    )


@dp.message(F.text == "🎁 تست رایگان")
async def free_trial_handler(
    message: Message,
):
    save_user(message.from_user)

    if has_claimed_trial(message.from_user.id):
        await message.answer(
            "⛔ شما قبلاً از تست رایگان استفاده کرده‌اید.\n"
            "هر کاربر فقط یک‌بار می‌تواند تست رایگان دریافت کند.",
            reply_markup=get_main_keyboard(),
        )
        return

    trial_settings = get_trial_settings()
    if trial_settings and trial_settings["category_id"] and trial_settings["active"]:
        category = get_category_with_panel(trial_settings["category_id"])
        if category:
            try:
                result = await provision_xui_subscription(
                    dict(category),
                    email=make_client_name_for_user(message.from_user.id, f"trial{int(time.time())}", prefix="trial"),
                    days=int(trial_settings["duration_days"] or 1),
                    volume_gb=float(trial_settings["volume_gb"] or 1),
                    telegram_id=message.from_user.id,
                )
                links = result["links"]
                if links:
                    save_trial_claim(message.from_user.id, "\n".join(links))
                    await send_subscription_to_user(
                        message.from_user.id,
                        title="🎁 تست رایگان شما فعال شد!",
                        links=links,
                        product_name="تست رایگان",
                        duration_days=int(trial_settings["duration_days"] or 1),
                        volume_gb=float(trial_settings["volume_gb"] or 1),
                    )
                    return
            except Exception as error:
                print("خطا در ساخت تست پنلی:", error)

    if get_trial_stock() <= 0:
        await message.answer(
            "😔 در حال حاضر موجودی تست رایگان تمام شده است.\n"
            "بعداً دوباره تلاش کن.",
            reply_markup=get_main_keyboard(),
        )
        return

    try:
        result = claim_trial(message.from_user.id)

    except Exception as error:
        print(
            "خطا هنگام واگذاری تست رایگان:",
            error,
        )

        await message.answer(
            "خطایی رخ داد. دوباره تلاش کن.",
            reply_markup=get_main_keyboard(),
        )
        return

    if not result["success"]:
        await message.answer(
            f"⛔ {result['message']}",
            reply_markup=get_main_keyboard(),
        )
        return

    safe_config = html.escape(result["config"])

    await message.answer(
        "🎁 <b>تست رایگان شما فعال شد!</b>\n\n"
        "🔐 <b>کانفیگ تست شما:</b>\n"
        f"<code>{safe_config}</code>\n\n"
        "کانفیگ را کپی کن و داخل برنامه اتصال وارد کن.",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "close_message")
async def close_message_callback(
    callback: CallbackQuery,
):
    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.answer()


# =========================================================
# دکمه ارسال رسید
# =========================================================

@dp.callback_query(F.data.startswith("send_receipt:"))
async def send_receipt_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    order_id = int(
        callback.data.split(":")[1]
    )

    order = get_order(order_id)

    if order is None:
        await callback.answer(
            "سفارش پیدا نشد.",
            show_alert=True,
        )
        return

    if order["telegram_id"] != callback.from_user.id:
        await callback.answer(
            "این سفارش متعلق به شما نیست.",
            show_alert=True,
        )
        return

    if order["status"] != "pending_payment":
        await callback.answer(
            "این سفارش قبلاً رسید گرفته یا بررسی شده است.",
            show_alert=True,
        )
        return

    await state.set_state(
        UserStates.waiting_payment_proof
    )

    await state.update_data(
        payment_order_id=order_id
    )

    await callback.message.answer(
        "📤 <b>حالا رسید پرداخت را ارسال کن.</b>\n\n"
        "می‌توانی عکس رسید کارت‌به‌کارت را بفرستی.\n"
        "اگر عکس نداری، متن رسید شامل مبلغ، "
        "زمان واریز و چهار رقم آخر کارت را ارسال کن.",
        parse_mode="HTML",
    )

    await callback.answer()


# =========================================================
# لغو سفارش
# =========================================================

@dp.callback_query(F.data.startswith("cancel_order:"))
async def cancel_order_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    order_id = int(
        callback.data.split(":")[1]
    )

    order = get_order(order_id)

    if order is None:
        await callback.answer(
            "سفارش پیدا نشد.",
            show_alert=True,
        )
        return

    if order["telegram_id"] != callback.from_user.id:
        await callback.answer(
            "این سفارش متعلق به شما نیست.",
            show_alert=True,
        )
        return

    cancelled = cancel_order(
        order_id=order_id,
        telegram_id=callback.from_user.id,
    )

    if not cancelled:
        await callback.answer(
            "این سفارش قابل لغو نیست.",
            show_alert=True,
        )
        return

    await state.clear()

    await callback.message.answer(
        "❌ سفارش لغو شد.",
        reply_markup=get_main_keyboard(),
    )

    await callback.answer(
        "سفارش لغو شد."
    )


# =========================================================
# دریافت عکس رسید
# =========================================================

@dp.message(
    UserStates.waiting_payment_proof,
    F.photo,
)
async def receive_photo_receipt(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    order_id = data.get(
        "payment_order_id"
    )

    if not order_id:
        await state.clear()

        await message.answer(
            "سفارش فعالی برای ارسال رسید وجود ندارد.",
            reply_markup=get_main_keyboard(),
        )
        return

    order = get_order(order_id)

    if order is None:
        await state.clear()

        await message.answer(
            "سفارش پیدا نشد.",
            reply_markup=get_main_keyboard(),
        )
        return

    if order["telegram_id"] != message.from_user.id:
        await message.answer(
            "این سفارش متعلق به شما نیست."
        )
        return

    if order["status"] != "pending_payment":
        await state.clear()

        await message.answer(
            "این سفارش قبلاً رسید گرفته یا بررسی شده است.",
            reply_markup=get_main_keyboard(),
        )
        return

    file_id = message.photo[-1].file_id
    caption = message.caption or ""

    updated = update_order_proof(
        order_id=order_id,
        proof_type="photo",
        proof_file_id=file_id,
        proof_text=caption,
    )

    if not updated:
        await state.clear()

        await message.answer(
            "رسید این سفارش قبلاً ثبت شده است.",
            reply_markup=get_main_keyboard(),
        )
        return

    await state.clear()

    await message.answer(
        "✅ رسید پرداخت با موفقیت دریافت شد.\n\n"
        "رسید برای ادمین ارسال شد. بعد از تأیید ادمین، "
        "اشتراک برایت ارسال می‌شود.",
        reply_markup=get_main_keyboard(),
    )

    await send_order_to_admins(order_id)


# =========================================================
# دریافت متن رسید
# =========================================================

@dp.message(
    UserStates.waiting_payment_proof,
    F.text,
)
async def receive_text_receipt(
    message: Message,
    state: FSMContext,
):
    if message.text == "❌ لغو":
        await state.clear()

        await message.answer(
            "ارسال رسید لغو شد.",
            reply_markup=get_main_keyboard(),
        )
        return

    data = await state.get_data()

    order_id = data.get(
        "payment_order_id"
    )

    if not order_id:
        await state.clear()

        await message.answer(
            "سفارش فعالی برای ارسال رسید وجود ندارد.",
            reply_markup=get_main_keyboard(),
        )
        return

    order = get_order(order_id)

    if order is None:
        await state.clear()

        await message.answer(
            "سفارش پیدا نشد.",
            reply_markup=get_main_keyboard(),
        )
        return

    if order["telegram_id"] != message.from_user.id:
        await message.answer(
            "این سفارش متعلق به شما نیست."
        )
        return

    if order["status"] != "pending_payment":
        await state.clear()

        await message.answer(
            "این سفارش قبلاً رسید گرفته یا بررسی شده است.",
            reply_markup=get_main_keyboard(),
        )
        return

    proof_text = message.text.strip()

    if len(proof_text) < 3:
        await message.answer(
            "متن رسید معتبر نیست. جزئیات واریز را ارسال کن."
        )
        return

    updated = update_order_proof(
        order_id=order_id,
        proof_type="text",
        proof_text=proof_text,
    )

    if not updated:
        await state.clear()

        await message.answer(
            "رسید این سفارش قبلاً ثبت شده است.",
            reply_markup=get_main_keyboard(),
        )
        return

    await state.clear()

    await message.answer(
        "✅ متن رسید دریافت شد.\n\n"
        "رسید برای ادمین ارسال شد. لطفا تا تایید رسید منتظر بمانید."
        " .بعد از تایید اشتراک خودکار برای شما ارسال میشود",
        reply_markup=get_main_keyboard(),
    )

    await send_order_to_admins(order_id)


# =========================================================
# تأیید سفارش توسط ادمین
# =========================================================

@dp.callback_query(F.data.startswith("approve_order:"))
async def approve_order_callback(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "شما ادمین نیستید.",
            show_alert=True,
        )
        return

    order_id = int(callback.data.split(":")[1])

    connection = get_db()
    order = connection.execute(
        """
        SELECT orders.*, products.name AS product_name, products.category_id,
               products.price, products.duration_days, products.volume_gb,
               xui_panels.base_url, xui_panels.api_token,
               xui_panels.subscription_url, categories.inbound_ids
        FROM orders JOIN products ON products.id = orders.product_id
        LEFT JOIN categories ON categories.id = products.category_id
        LEFT JOIN xui_panels ON xui_panels.id = categories.panel_id
        WHERE orders.id = ?
        """,
        (order_id,),
    ).fetchone()
    connection.close()
    if order is None:
        await callback.answer("سفارش پیدا نشد.", show_alert=True)
        return

    if order["category_id"] is not None:
        try:
            result = await approve_xui_order(
                order_id=order_id,
                approved_by=callback.from_user.id,
            )
        except XUIError as error:
            await callback.answer(str(error), show_alert=True)
            return
        except Exception as error:
            print("خطا هنگام ساخت اشتراک در پنل:", error)
            await callback.answer("ساخت اشتراک در پنل ناموفق بود؛ سفارش برای تلاش دوباره باقی ماند.", show_alert=True)
            return
        if not result or not result.get("success"):
            await callback.answer((result or {}).get("message", "تأیید انجام نشد."), show_alert=True)
            return
    else:
        try:
            result = approve_order(
                order_id=order_id,
                approved_by=callback.from_user.id,
            )
        except Exception as error:
            print(
                "خطا هنگام تأیید سفارش:",
                error,
            )

            await callback.answer(
                "خطا هنگام تأیید سفارش.",
                show_alert=True,
            )
            return

    if not result["success"]:
        await callback.answer(
            result["message"],
            show_alert=True,
        )
        return

    try:
        await send_product_to_user(result)

    except Exception as error:
        print(
            "خطا در ارسال کانفیگ برای کاربر:",
            error,
        )

    try:
        await callback.message.edit_reply_markup(
            reply_markup=None
        )
    except Exception:
        pass

    await callback.message.answer(
        f"✅ سفارش شماره "
        f"<code>{order_id}</code> تأیید شد.\n"
        "کانفیگ برای کاربر ارسال شد.",
        parse_mode="HTML",
    )

    await callback.answer(
        "پرداخت تأیید شد."
    )


# =========================================================
# رد سفارش توسط ادمین
# =========================================================

@dp.callback_query(F.data.startswith("reject_order:"))
async def reject_order_callback(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "شما ادمین نیستید.",
            show_alert=True,
        )
        return

    order_id = int(
        callback.data.split(":")[1]
    )

    rejected = reject_order(
        order_id=order_id,
        admin_id=callback.from_user.id,
    )

    if not rejected:
        await callback.answer(
            "این سفارش قبلاً بررسی شده است.",
            show_alert=True,
        )
        return

    order = get_order(order_id)

    if order:
        try:
            await bot.send_message(
                order["telegram_id"],
                "❌ رسید پرداخت شما رد شد.\n\n"
                "اگر فکر می‌کنی اشتباهی رخ داده، "
                "با پشتیبانی تماس بگیر.",
                reply_markup=get_main_keyboard(),
            )
        except Exception as error:
            print(
                "خطا در ارسال پیام رد سفارش:",
                error,
            )

    try:
        await callback.message.edit_reply_markup(
            reply_markup=None
        )
    except Exception:
        pass

    await callback.message.answer(
        f"❌ سفارش شماره "
        f"<code>{order_id}</code> رد شد.",
        parse_mode="HTML",
    )

    await callback.answer(
        "سفارش رد شد."
    )


# =========================================================
# تعرفه‌ها
# =========================================================

@dp.message(F.text == "📦 اشتراک‌های من")
async def my_subscriptions_handler(
    message: Message,
):
    save_user(message.from_user)

    orders = get_user_approved_orders(
        message.from_user.id
    )

    trial_claim = get_user_trial_claim(
        message.from_user.id
    )

    if not orders and not trial_claim:
        await message.answer(
            "📦 هنوز هیچ اشتراک فعالی نداری.\n\n"
            "برای خرید، از دکمه «🛒 خرید اشتراک» استفاده کن.",
            reply_markup=get_main_keyboard(),
        )
        return

    text = "📦 <b>اشتراک‌های من</b>\n\n"

    if trial_claim:
        trial_subscription = trial_claim["config"] or "—"
        text += (
            "🎁 <b>تست رایگان</b>\n"
            f"📅 تاریخ دریافت: {trial_claim['claimed_at']}\n"
            f"🔗 Subscription:\n<code>{html.escape(trial_subscription)}</code>\n\n"
        )

    for order in orders:
        subscription = order["subscription_url"] or order["delivered_config"] or "—"
        text += (
            f"🛍 <b>{html.escape(order['product_name'])}</b>\n"
            f"⏳ مدت: {order['duration_days']} روز\n"
            f"📊 حجم: {order['volume_gb']} GB\n"
            f"📅 تاریخ فعال‌سازی: {order['approved_at']}\n"
            f"🔗 Subscription:\n<code>{html.escape(subscription)}</code>\n\n"
        )

    await message.answer(
        text,
        reply_markup=subscriptions_keyboard(orders),
        parse_mode="HTML",
    )


@dp.callback_query(F.data.startswith("subscription_traffic:"))
async def subscription_traffic_callback(callback: CallbackQuery):
    try:
        order_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("شناسه اشتراک معتبر نیست.", show_alert=True)
        return
    connection = get_db()
    order = connection.execute(
        """
        SELECT orders.*, products.name AS product_name, products.category_id,
               xui_panels.base_url, xui_panels.api_token,
               xui_panels.subscription_url
        FROM orders JOIN products ON products.id = orders.product_id
        LEFT JOIN categories ON categories.id = products.category_id
        LEFT JOIN xui_panels ON xui_panels.id = categories.panel_id
        WHERE orders.id = ? AND orders.telegram_id = ? AND orders.status = 'approved'
        """,
        (order_id, callback.from_user.id),
    ).fetchone()
    connection.close()
    if order is None:
        await callback.answer("اشتراک پیدا نشد.", show_alert=True)
        return
    if not order["xui_email"] or not order["category_id"] or not order["base_url"]:
        await callback.answer("برای این اشتراک اطلاعات مصرف پنل در دسترس نیست.", show_alert=True)
        return
    try:
        traffic = await XUIClient(order).get_traffic(order["xui_email"])
    except XUIError as error:
        await callback.answer(str(error), show_alert=True)
        return
    await callback.message.answer(
        f"📊 <b>وضعیت اشتراک {html.escape(order['product_name'])}</b>\n\n"
        f"{format_traffic_status(traffic)}",
        parse_mode="HTML",
    )
    await callback.answer()


# =========================================================
# آموزش و پشتیبانی
# =========================================================

@dp.message(F.text == "📚 آموزش اتصال")
async def tutorial_handler(
    message: Message,
):
    await message.answer(
        "📚 <b>آموزش اتصال</b>\n\n"
        "سیستم‌عامل دستگاه خودت را انتخاب کن:",
        reply_markup=tutorial_os_keyboard(),
        parse_mode="HTML",
    )


@dp.callback_query(F.data.startswith("tut_os:"))
async def tutorial_os_callback(
    callback: CallbackQuery,
):
    os_key = callback.data.split(":")[1]

    os_data = TUTORIAL_STRUCTURE.get(os_key)

    if os_data is None:
        await callback.answer(
            "سیستم‌عامل پیدا نشد.",
            show_alert=True,
        )
        return

    try:
        await callback.message.edit_text(
            f"📚 <b>آموزش اتصال - {os_data['label']}</b>\n\n"
            "کلاینت (برنامه اتصال) خودت را انتخاب کن:",
            reply_markup=tutorial_client_keyboard(os_key),
            parse_mode="HTML",
        )
    except Exception:
        pass

    await callback.answer()


@dp.callback_query(F.data == "tut_back_os")
async def tutorial_back_os_callback(
    callback: CallbackQuery,
):
    try:
        await callback.message.edit_text(
            "📚 <b>آموزش اتصال</b>\n\n"
            "سیستم‌عامل دستگاه خودت را انتخاب کن:",
            reply_markup=tutorial_os_keyboard(),
            parse_mode="HTML",
        )
    except Exception:
        pass

    await callback.answer()


@dp.callback_query(F.data.startswith("tut_client:"))
async def tutorial_client_callback(
    callback: CallbackQuery,
):
    _, os_key, client_key = callback.data.split(":")

    os_data = TUTORIAL_STRUCTURE.get(os_key)

    if os_data is None or client_key not in os_data["clients"]:
        await callback.answer(
            "کلاینت پیدا نشد.",
            show_alert=True,
        )
        return

    client_label = os_data["clients"][client_key]

    video = get_tutorial_video(os_key, client_key)

    if video is None:
        await callback.answer(
            "🎬 ویدیوی آموزشی این کلاینت هنوز "
            "توسط ادمین ثبت نشده است.",
            show_alert=True,
        )
        return

    try:
        await bot.copy_message(
            chat_id=callback.from_user.id,
            from_chat_id=video["chat_id"],
            message_id=video["message_id"],
        )

        await callback.message.answer(
            f"📚 ویدیوی آموزش اتصال "
            f"«{os_data['label']} - {client_label}» "
            "ارسال شد.",
            reply_markup=get_main_keyboard(),
        )

    except Exception as error:
        print(
            "خطا در ارسال ویدیوی آموزشی:",
            error,
        )

        await callback.message.answer(
            "❌ خطا در ارسال ویدیو. با پشتیبانی تماس بگیر.",
            reply_markup=get_main_keyboard(),
        )

    await callback.answer()


@dp.message(F.text == "🆘 پشتیبانی")
async def support_handler(
    message: Message,
):
    if SUPPORT_USERNAME:
        await message.answer(
            "🆘 <b>پشتیبانی</b>\n\n"
            "برای ارتباط با پشتیبانی روی آیدی زیر بزن:\n"
            f"{html.escape(SUPPORT_USERNAME)}",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML",
        )
        return

    await message.answer(
        "🆘 برای پشتیبانی، پیام خود را همین‌جا ارسال کن.",
        reply_markup=get_main_keyboard(),
    )


# =========================================================
# حساب کاربری
# =========================================================

@dp.message(F.text == "👤 حساب کاربری")
async def account_handler(
    message: Message,
):
    save_user(message.from_user)

    username = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else "بدون یوزرنیم"
    )

    user = get_user(message.from_user.id)
    balance = float(user["balance"]) if user else 0.0

    await message.answer(
        "👤 <b>حساب کاربری</b>\n\n"
        f"🆔 آیدی: "
        f"<code>{message.from_user.id}</code>\n"
        f"👤 نام: "
        f"{html.escape(message.from_user.first_name or '')}\n"
        f"🔗 یوزرنیم: "
        f"{html.escape(username)}\n\n"
        f"👛 موجودی کیف پول: "
        f"<b>{balance:,.0f}</b> تومان",
        reply_markup=account_panel_keyboard(),
        parse_mode="HTML",
    )


# =========================================================
# شارژ کیف پول توسط کاربر
# =========================================================

@dp.callback_query(F.data == "topup_start")
async def topup_start_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    save_user(callback.from_user)

    await state.set_state(
        UserStates.waiting_topup_amount
    )

    await callback.message.answer(
        "💰 مبلغی که می‌خواهی به کیف پول خود شارژ کنی "
        "را به تومان ارسال کن:",
        reply_markup=cancel_keyboard,
    )

    await callback.answer()


@dp.message(UserStates.waiting_topup_amount)
async def receive_topup_amount(
    message: Message,
    state: FSMContext,
):
    if message.text == "❌ لغو":
        await state.clear()

        await message.answer(
            "شارژ کیف پول لغو شد.",
            reply_markup=get_main_keyboard(),
        )
        return

    value = (
        message.text.strip().replace(",", "")
        if message.text
        else ""
    )

    try:
        amount = Decimal(value)
    except InvalidOperation:
        await message.answer(
            "مبلغ واردشده معتبر نیست. دوباره ارسال کن."
        )
        return

    if amount <= 0:
        await message.answer(
            "مبلغ باید بیشتر از صفر باشد."
        )
        return

    await state.clear()

    topup = create_topup_request(
        telegram_id=message.from_user.id,
        amount=float(amount),
    )

    await message.answer(
        "💳 <b>شارژ کیف پول با کارت‌به‌کارت</b>\n\n"
        f"💰 مبلغ: "
        f"<b>{float(topup['amount']):,.0f}</b> تومان\n\n"
        "لطفاً مبلغ دقیق را به شماره کارت زیر "
        "کارت‌به‌کارت کن:\n\n"
        f"💳 شماره کارت:\n"
        f"<code>{html.escape(CARD_NUMBER)}</code>\n\n"
        f"👤 به نام: "
        f"<b>{html.escape(CARD_OWNER)}</b>\n\n"
        "بعد از انجام کارت‌به‌کارت، روی دکمه "
        "«ارسال رسید پرداخت» بزن و عکس رسید را ارسال کن.\n\n"
        f"⏱ اگر ادمین تا {AUTO_APPROVE_MINUTES} دقیقه "
        "رسید را بررسی نکند، شارژ خودکار تأیید می‌شود.",
        reply_markup=topup_payment_keyboard(
            topup["id"]
        ),
        parse_mode="HTML",
    )


@dp.callback_query(F.data.startswith("send_topup_receipt:"))
async def send_topup_receipt_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    topup_id = int(callback.data.split(":")[1])

    topup = get_topup(topup_id)

    if topup is None:
        await callback.answer(
            "درخواست پیدا نشد.",
            show_alert=True,
        )
        return

    if topup["telegram_id"] != callback.from_user.id:
        await callback.answer(
            "این درخواست متعلق به شما نیست.",
            show_alert=True,
        )
        return

    if topup["status"] != "pending_payment":
        await callback.answer(
            "این درخواست قبلاً رسید گرفته یا بررسی شده است.",
            show_alert=True,
        )
        return

    await state.set_state(
        UserStates.waiting_topup_proof
    )

    await state.update_data(topup_id=topup_id)

    await callback.message.answer(
        "📤 <b>حالا رسید پرداخت را ارسال کن.</b>\n\n"
        "می‌توانی عکس رسید کارت‌به‌کارت را بفرستی.\n"
        "اگر عکس نداری، متن رسید شامل مبلغ، "
        "زمان واریز و چهار رقم آخر کارت را ارسال کن.",
        parse_mode="HTML",
    )

    await callback.answer()


@dp.callback_query(F.data.startswith("cancel_topup:"))
async def cancel_topup_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    topup_id = int(callback.data.split(":")[1])

    topup = get_topup(topup_id)

    if topup is None:
        await callback.answer(
            "درخواست پیدا نشد.",
            show_alert=True,
        )
        return

    if topup["telegram_id"] != callback.from_user.id:
        await callback.answer(
            "این درخواست متعلق به شما نیست.",
            show_alert=True,
        )
        return

    cancelled = cancel_topup(
        topup_id=topup_id,
        telegram_id=callback.from_user.id,
    )

    if not cancelled:
        await callback.answer(
            "این درخواست قابل لغو نیست.",
            show_alert=True,
        )
        return

    await state.clear()

    await callback.message.answer(
        "❌ درخواست شارژ لغو شد.",
        reply_markup=get_main_keyboard(),
    )

    await callback.answer("لغو شد.")


async def send_topup_to_admins(topup_id: int):
    topup = get_topup(topup_id)

    if topup is None:
        return

    username_text = "بدون یوزرنیم"

    connection = get_db()

    user = connection.execute(
        """
        SELECT *
        FROM users
        WHERE telegram_id = ?
        """,
        (topup["telegram_id"],),
    ).fetchone()

    connection.close()

    if user and user["username"]:
        username_text = "@" + html.escape(user["username"])

    proof_text = html.escape(
        topup["proof_text"] or "بدون توضیح"
    )

    admin_text = (
        "👛 <b>درخواست شارژ کیف پول جدید</b>\n\n"
        f"🧾 شماره درخواست: "
        f"<code>{topup['id']}</code>\n"
        f"🆔 آیدی کاربر: "
        f"<code>{topup['telegram_id']}</code>\n"
        f"👤 یوزرنیم: {username_text}\n"
        f"💰 مبلغ: "
        f"<b>{topup['amount']:,.0f}</b> تومان\n"
        f"📝 توضیحات رسید:\n{proof_text}\n\n"
        f"⏰ پایان زمان بررسی: "
        f"<code>{topup['expires_at']}</code>"
    )

    for admin_id in ADMIN_IDS:
        try:
            if (
                topup["proof_type"] == "photo"
                and topup["proof_file_id"]
            ):
                await bot.send_photo(
                    chat_id=admin_id,
                    photo=topup["proof_file_id"],
                    caption=admin_text,
                    parse_mode="HTML",
                    reply_markup=admin_topup_keyboard(
                        topup_id
                    ),
                )
            else:
                await bot.send_message(
                    chat_id=admin_id,
                    text=admin_text,
                    parse_mode="HTML",
                    reply_markup=admin_topup_keyboard(
                        topup_id
                    ),
                )

        except Exception as error:
            print(
                "خطا در ارسال درخواست شارژ برای ادمین:",
                error,
            )


@dp.message(
    UserStates.waiting_topup_proof,
    F.photo,
)
async def receive_topup_photo_receipt(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    topup_id = data.get("topup_id")

    if not topup_id:
        await state.clear()

        await message.answer(
            "درخواست فعالی برای ارسال رسید وجود ندارد.",
            reply_markup=get_main_keyboard(),
        )
        return

    topup = get_topup(topup_id)

    if topup is None:
        await state.clear()

        await message.answer(
            "درخواست پیدا نشد.",
            reply_markup=get_main_keyboard(),
        )
        return

    if topup["telegram_id"] != message.from_user.id:
        await message.answer(
            "این درخواست متعلق به شما نیست."
        )
        return

    if topup["status"] != "pending_payment":
        await state.clear()

        await message.answer(
            "این درخواست قبلاً رسید گرفته یا بررسی شده است.",
            reply_markup=get_main_keyboard(),
        )
        return

    file_id = message.photo[-1].file_id
    caption = message.caption or ""

    updated = update_topup_proof(
        topup_id=topup_id,
        proof_type="photo",
        proof_file_id=file_id,
        proof_text=caption,
    )

    if not updated:
        await state.clear()

        await message.answer(
            "رسید این درخواست قبلاً ثبت شده است.",
            reply_markup=get_main_keyboard(),
        )
        return

    await state.clear()

    await message.answer(
        "✅ متن رسید دریافت شد.\n\n"
        "رسید برای ادمین ارسال شد. لطفا تا تایید رسید منتظر بمانید."
        " .بعد از تایید اشتراک خودکار برای شما ارسال میشود",
        reply_markup=get_main_keyboard(),
    )

    await send_topup_to_admins(topup_id)


@dp.message(
    UserStates.waiting_topup_proof,
    F.text,
)
async def receive_topup_text_receipt(
    message: Message,
    state: FSMContext,
):
    if message.text == "❌ لغو":
        await state.clear()

        await message.answer(
            "ارسال رسید لغو شد.",
            reply_markup=get_main_keyboard(),
        )
        return

    data = await state.get_data()

    topup_id = data.get("topup_id")

    if not topup_id:
        await state.clear()

        await message.answer(
            "درخواست فعالی برای ارسال رسید وجود ندارد.",
            reply_markup=get_main_keyboard(),
        )
        return

    topup = get_topup(topup_id)

    if topup is None:
        await state.clear()

        await message.answer(
            "درخواست پیدا نشد.",
            reply_markup=get_main_keyboard(),
        )
        return

    if topup["telegram_id"] != message.from_user.id:
        await message.answer(
            "این درخواست متعلق به شما نیست."
        )
        return

    if topup["status"] != "pending_payment":
        await state.clear()

        await message.answer(
            "این درخواست قبلاً رسید گرفته یا بررسی شده است.",
            reply_markup=get_main_keyboard(),
        )
        return

    proof_text = message.text.strip()

    if len(proof_text) < 3:
        await message.answer(
            "متن رسید معتبر نیست. جزئیات واریز را ارسال کن."
        )
        return

    updated = update_topup_proof(
        topup_id=topup_id,
        proof_type="text",
        proof_text=proof_text,
    )

    if not updated:
        await state.clear()

        await message.answer(
            "رسید این درخواست قبلاً ثبت شده است.",
            reply_markup=get_main_keyboard(),
        )
        return

    await state.clear()

    await message.answer(
        "✅ متن رسید دریافت شد.\n\n"
        "رسید برای ادمین ارسال شد. بعد از تأیید ادمین، "
        "کیف پول شما شارژ می‌شود.",
        reply_markup=get_main_keyboard(),
    )

    await send_topup_to_admins(topup_id)


# =========================================================
# تأیید / رد شارژ کیف پول توسط ادمین
# =========================================================

@dp.callback_query(F.data.startswith("approve_topup:"))
async def approve_topup_callback(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "شما ادمین نیستید.",
            show_alert=True,
        )
        return

    topup_id = int(callback.data.split(":")[1])

    try:
        result = approve_topup(
            topup_id=topup_id,
            approved_by=callback.from_user.id,
        )

    except Exception as error:
        print(
            "خطا هنگام تأیید شارژ:",
            error,
        )

        await callback.answer(
            "خطا هنگام تأیید شارژ.",
            show_alert=True,
        )
        return

    if not result["success"]:
        await callback.answer(
            result["message"],
            show_alert=True,
        )
        return

    try:
        await bot.send_message(
            result["telegram_id"],
            "✅ <b>کیف پول شما شارژ شد.</b>\n\n"
            f"💰 مبلغ: "
            f"<b>{result['amount']:,.0f}</b> تومان\n"
            f"👛 موجودی جدید: "
            f"<b>{result['new_balance']:,.0f}</b> تومان",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(),
        )

    except Exception as error:
        print(
            "خطا در اطلاع‌رسانی شارژ به کاربر:",
            error,
        )

    try:
        await callback.message.edit_reply_markup(
            reply_markup=None
        )
    except Exception:
        pass

    await callback.message.answer(
        f"✅ درخواست شارژ شماره "
        f"<code>{topup_id}</code> تأیید شد.",
        parse_mode="HTML",
    )

    await callback.answer("شارژ تأیید شد.")


@dp.callback_query(F.data.startswith("reject_topup:"))
async def reject_topup_callback(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "شما ادمین نیستید.",
            show_alert=True,
        )
        return

    topup_id = int(callback.data.split(":")[1])

    rejected = reject_topup(
        topup_id=topup_id,
        admin_id=callback.from_user.id,
    )

    if not rejected:
        await callback.answer(
            "این درخواست قبلاً بررسی شده است.",
            show_alert=True,
        )
        return

    topup = get_topup(topup_id)

    if topup:
        try:
            await bot.send_message(
                topup["telegram_id"],
                "❌ رسید شارژ کیف پول شما رد شد.\n\n"
                "اگر فکر می‌کنی اشتباهی رخ داده، "
                "با پشتیبانی تماس بگیر.",
                reply_markup=get_main_keyboard(),
            )
        except Exception as error:
            print(
                "خطا در ارسال پیام رد شارژ:",
                error,
            )

    try:
        await callback.message.edit_reply_markup(
            reply_markup=None
        )
    except Exception:
        pass

    await callback.message.answer(
        f"❌ درخواست شارژ شماره "
        f"<code>{topup_id}</code> رد شد.",
        parse_mode="HTML",
    )

    await callback.answer("رد شد.")


async def main():
    if not bot:
        raise RuntimeError("BOT_TOKEN is required when starting the Telegram bot.")
    init_database()
    global main_keyboard
    main_keyboard = get_main_keyboard()
    load_extra_admins()

    auto_worker = asyncio.create_task(
        auto_approve_worker()
    )

    backup_task = asyncio.create_task(
        backup_worker()
    )

    web_server = None
    web_task = None
    if os.getenv("WEB_WITH_BOT", "1") == "1":
        import uvicorn
        web_config = uvicorn.Config(
            app,
            host=os.getenv("WEB_HOST", "127.0.0.1"),
            port=int(os.getenv("WEB_PORT", "8090")),
            log_level="info",
        )
        web_server = uvicorn.Server(web_config)
        web_task = asyncio.create_task(web_server.serve())

    try:
        # اجرای محلی با polling با webhook هم‌زمان نمی‌شود.
        # webhook قبلی را پاک می‌کنیم و پیام‌های معوقه را نگه می‌داریم.
        webhook_ready = await delete_webhook_with_retry(bot, attempts=3, base_delay=2)
        if webhook_ready:
            print("Telegram webhook cleared.")
        else:
            print("Telegram is currently unreachable; polling will continue and retry.")
        print("Bot started...")

        # اطلاع‌رسانی خودکار نصب/راه‌اندازی موفق به سوپرادمین‌ها.
        # فقط یک‌بار در هر استارتاپ ارسال می‌شود و مقادیر حساس را شامل نمی‌شود.
        async def notify_admins_startup():
            try:
                me = await bot.get_me()
            except Exception as error:
                print("خطا در دریافت اطلاعات ربات:", error)
                return
            web_port = os.getenv("WEB_PORT", "8090")
            # آی‌پی عمومی واقعی سرور را از .env می‌خوانیم (نصب‌کننده آن را با
            # WEB_PUBLIC_IP تنظیم می‌کند) تا آدرس پنل درست نمایش داده شود.
            public_ip = os.getenv("WEB_PUBLIC_IP") or os.getenv("SERVER_IP", "")
            panel_address = f"http://{public_ip}:{web_port}/admin"
            message = (
                "✅ <b>نصب و راه‌اندازی با موفقیت انجام شد</b>\n\n"
                f"🤖 ربات: @{html.escape(me.username or '')}\n"
                f"📡 وضعیت ربات: <b>فعال</b>\n"
                f"🌐 آدرس وب‌پنل: <code>{html.escape(panel_address)}</code>\n\n"
                "🛠 پنل مدیریت ترمینال:\n"
                "<code>sudo aval-bot-menu</code>\n\n"
                "⚙️ تنظیمات از داخل وب‌پنل در بخش «کنترل Bot و تنظیمات» قابل تغییر است."
            )
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, message, parse_mode="HTML")
                except Exception as error:
                    print("خطا در ارسال پیام نصب به ادمین:", error)

        asyncio.create_task(notify_admins_startup())

        await dp.start_polling(bot)

    finally:
        if web_server:
            web_server.should_exit = True
        if web_task:
            web_task.cancel()
        auto_worker.cancel()
        backup_task.cancel()

        for task in (auto_worker, backup_task, web_task):
            if task:
                try:
                    await task
                except asyncio.CancelledError:
                    pass


if __name__ == "__main__":
    import asyncio
    import uvicorn
    if os.getenv("WEB_ONLY", "0") == "1":
        uvicorn.run(app, host=os.getenv("WEB_HOST", "127.0.0.1"), port=int(os.getenv("WEB_PORT", "8090")))
    else:
        asyncio.run(main())