# filename: telegram_bot_only.py
import asyncio
import json
import os
import random
import string
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button, functions, errors

# ---------- تعديل القيم هنان ----------
API_ID = 18421930
API_HASH = "9cf3a6feb6dfcc7c02c69eb2c286830e"
BOT_TOKEN = "5876070267:AAEN89CArFut-2ObR2BpbT5Oq4QhQQX3Jww"
GROUP_LINK_CHANNEL = -1001234567890  # خلي هذا ID القناة أو استخدم username ك str "@MyChannel"
ADMIN_ID = 5841353971
# --------------------------------------

# ---------- ملفات الDB ----------
LINKS_FILE = "user_group_links.json"
CODES_FILE = "codes_database.json"
LOG_FILE = "operations_log.json"
BANNED_FILE = "banned_users.json"
CONFIG_FILE = "bot_config.json"
# --------------------------------

# ---------- Helpers ----------
def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default
    return default

def save_link_db(data):
    save_json(LINKS_FILE, data)

def load_link_db():
    return load_json(LINKS_FILE, {})

def save_codes_db(data):
    save_json(CODES_FILE, data)

def load_codes_db():
    return load_json(CODES_FILE, {"codes": {}, "user_access": {}, "user_stats": {}, "daily_limits": {}})

def save_log_entry(entry):
    log = load_json(LOG_FILE, [])
    log.append(entry)
    save_json(LOG_FILE, log)

def load_banned_users():
    return load_json(BANNED_FILE, [])

def save_banned_users(data):
    save_json(BANNED_FILE, data)

def load_config():
    return load_json(CONFIG_FILE, {"user_settings": {}})

def ensure_user_links(user_id):
    db = load_link_db()
    return db.setdefault(str(user_id), [])

def add_group_link(user_id, group_id, title, link):
    db = load_link_db()
    lst = db.setdefault(str(user_id), [])
    # تفادي تكرار نفس الـ group_id
    if not any(x.get("group_id")==group_id for x in lst):
        lst.append({
            "group_id": group_id,
            "title": title,
            "link": link,
            "created_at": datetime.now().isoformat()
        })
        save_link_db(db)

def get_user_links(user_id):
    db = load_link_db()
    return db.get(str(user_id), [])

def get_all_links():
    db = load_link_db()
    all_links = []
    for uid, links in db.items():
        for l in links:
            l2 = l.copy()
            l2["owner"] = uid
            all_links.append(l2)
    return all_links

def user_is_banned(user_id):
    banned = load_banned_users()
    return str(user_id) in banned

def ban_user(user_id):
    banned = load_banned_users()
    if str(user_id) not in banned:
        banned.append(str(user_id))
        save_banned_users(banned)

# Codes system
DEFAULT_ACCESS_HOURS = 24
def generate_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=6))

def create_new_code(duration_hours=None):
    db = load_codes_db()
    new_code = generate_code()
    while new_code in db["codes"]:
        new_code = generate_code()
    if duration_hours is None:
        duration_hours = DEFAULT_ACCESS_HOURS
    db["codes"][new_code] = {
        "used": False,
        "created_at": datetime.now().isoformat(),
        "duration_hours": duration_hours
    }
    save_codes_db(db)
    return new_code, duration_hours

def use_code(code, user_id):
    db = load_codes_db()
    code = code.upper()
    if code not in db["codes"]:
        return False, "كود غير صحيح"
    if db["codes"][code].get("used"):
        return False, "الكود مستخدم مسبقاً"
    duration_hours = db["codes"][code].get("duration_hours", DEFAULT_ACCESS_HOURS)
    expiry = datetime.now() + timedelta(hours=duration_hours)
    db["user_access"][str(user_id)] = {
        "granted_at": datetime.now().isoformat(),
        "expires_at": expiry.isoformat(),
        "code_used": code,
        "duration_hours": duration_hours
    }
    db["codes"][code]["used"] = True
    db["codes"][code]["used_by"] = str(user_id)
    db["codes"][code]["used_at"] = datetime.now().isoformat()
    db.setdefault("user_stats", {}).setdefault(str(user_id), {"groups_created": 0, "last_activity": ""})
    save_codes_db(db)
    return True, f"تم منح الوصول لمدة {duration_hours} ساعة"

def check_user_access(user_id):
    db = load_codes_db()
    s = str(user_id)
    if s not in db.get("user_access", {}):
        return False, "لا يوجد وصول"
    user_data = db["user_access"][s]
    expiry = datetime.fromisoformat(user_data["expires_at"])
    if datetime.now() > expiry:
        del db["user_access"][s]
        save_codes_db(db)
        return False, "انتهت صلاحية الوصول"
    return True, "وصول صالح"

def check_daily_limit(user_id, requested_groups):
    db = load_codes_db()
    s = str(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    db.setdefault("daily_limits", {})
    db["daily_limits"].setdefault(s, {})
    db["daily_limits"][s].setdefault(today, 0)
    current = db["daily_limits"][s][today]
    daily_limit = 100
    if user_id == ADMIN_ID:
        daily_limit = 1000
    if current + requested_groups > daily_limit:
        return False, f"تجاوزت الحد اليومي! استخدمت {current}/{daily_limit} مجموعة اليوم"
    return True, "ضمن الحد"

def update_daily_usage(user_id, groups_created):
    db = load_codes_db()
    s = str(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    db.setdefault("daily_limits", {})
    db["daily_limits"].setdefault(s, {})
    db["daily_limits"][s].setdefault(today, 0)
    db["daily_limits"][s][today] += groups_created
    db.setdefault("user_stats", {})
    db["user_stats"].setdefault(s, {"groups_created": 0, "last_activity": ""})
    db["user_stats"][s]["groups_created"] += groups_created
    db["user_stats"][s]["last_activity"] = datetime.now().isoformat()
    save_codes_db(db)

# Settings per user
def get_user_settings(user_id):
    cfg = load_config()
    us = cfg.setdefault("user_settings", {}).setdefault(str(user_id), {})
    us.setdefault("delay_between_groups", 5)
    save_json(CONFIG_FILE, cfg)
    return us

def set_user_setting(user_id, key, value):
    cfg = load_config()
    cfg.setdefault("user_settings", {}).setdefault(str(user_id), {})[key] = value
    save_json(CONFIG_FILE, cfg)

# --------------------------------

# ---------- البوت ----------
bot_client = TelegramClient("bot_session", API_ID, API_HASH)

@bot_client.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    user_id = event.sender_id
    if user_is_banned(user_id):
        await event.respond("❌ آسف، محظور من استخدام البوت.")
        return

    if user_id == ADMIN_ID:
        buttons = [
            [Button.inline("🎫 توليد كود سريع", b"gen_code")],
            [Button.inline("🎫 كود مخصص", b"gen_code_custom")],
            [Button.inline("📋 عرض اللوق", b"view_log")],
            [Button.inline("🚫 حظر شخص", b"ban_user")],
            [Button.inline("🔎 استخراج كل الروابط", b"extract_all_links")],
        ]
        await event.respond("👑 أهلاً أدوووم، شنو تريد؟", buttons=buttons)
        return

    has_access, msg = check_user_access(user_id)
    if has_access:
        buttons = [
            [Button.inline("➕ حفظ رابط كروب", b"add_link")],
            [Button.inline("📤 إرسال روابطي للقناة", b"send_links_channel")],
            [Button.inline("📥 استخراج روابطي", b"get_links")],
            [Button.inline("🚪 خروج البوت من مجموعاتي", b"leave_groups")],
            [Button.inline("⚡️ سرعة الإنشاء (تأخير)", b"speed_setting")],
            [Button.inline("🛠️ إنشاء كروبات (غير متوفر للبوت)", b"create_groups")],
        ]
        await event.respond("✅ عندك وصول. شنو تريد تسوي؟", buttons=buttons)
    else:
        await event.respond("🔑 أدخل كود الوصول المكوّن من 6 أحرف عالخاص:")

@bot_client.on(events.NewMessage)
async def code_listener(event):
    user_id = event.sender_id
    if event.text is None:
        return
    if event.text.startswith('/'):
        return
    if user_is_banned(user_id):
        await event.respond("❌ محظور.")
        return
    has_access, _ = check_user_access(user_id)
    if has_access:
        return  # already has access, ignore plain messages
    txt = event.text.strip().upper()
    if len(txt) == 6 and txt.isalnum():
        ok, message = use_code(txt, user_id)
        if ok:
            buttons = [
                [Button.inline("➕ حفظ رابط كروب", b"add_link")],
                [Button.inline("📤 إرسال روابطي للقناة", b"send_links_channel")],
                [Button.inline("📥 استخراج روابطي", b"get_links")],
            ]
            await event.respond(f"✅ {message}\nاختر اللي تريده:", buttons=buttons)
        else:
            await event.respond(f"❌ {message}")
    else:
        # رسالة عامة أو دليل غير مراد
        return

@bot_client.on(events.CallbackQuery)
async def cb_handler(event):
    user_id = event.sender_id
    data = event.data
    if user_is_banned(user_id):
        await event.answer("❌ محظور.")
        return

    # ============ ADMIN =============
    if user_id == ADMIN_ID:
        if data == b"gen_code":
            code, dur = create_new_code()
            save_log_entry({"user_id": user_id, "operation": "gen_code", "details": code, "timestamp": datetime.now().isoformat()})
            await event.answer()
            await event.respond(f"🎫 كود سريع: `{code}`\n⏰ مدة: {dur} ساعة")
            return
        if data == b"gen_code_custom":
            await event.answer()
            async with bot_client.conversation(user_id) as conv:
                await conv.send_message("⏱️ دخل عدد الساعات للكود:")
                r = await conv.get_response()
                try:
                    h = int(r.text.strip())
                    if h <= 0:
                        await conv.send_message("❌ لازم يكون الرقم > 0")
                    else:
                        code, dur = create_new_code(h)
                        save_log_entry({"user_id": user_id, "operation": "gen_code_custom", "details": f"{code} ({dur}h)", "timestamp": datetime.now().isoformat()})
                        await conv.send_message(f"✅ كود: `{code}`\n⏰ مدة: {dur} ساعة")
                except:
                    await conv.send_message("❌ أدخل رقم صحيح!")
            return
        if data == b"view_log":
            await event.answer()
            log = load_json(LOG_FILE, [])
            txt = "📋 سجل العمليات (الأخير):\n\n"
            for e in log[-20:]:
                txt += f"{e.get('timestamp','?')}: {e.get('user_id','?')} - {e.get('operation','?')} - {e.get('details','')}\n"
            await event.respond(txt or "لا يوجد لوق.")
            return
        if data == b"ban_user":
            await event.answer()
            async with bot_client.conversation(user_id) as conv:
                await conv.send_message("🚫 اكتب ID الشخص لحظره:")
                r = await conv.get_response()
                tid = r.text.strip()
                if tid.isdigit():
                    ban_user(tid)
                    save_log_entry({"user_id": user_id, "operation": "ban", "details": tid, "timestamp": datetime.now().isoformat()})
                    await conv.send_message(f"✅ تم حظر: {tid}")
                else:
                    await conv.send_message("❌ هذا مو ID صحيح.")
            return
        if data == b"extract_all_links":
            await event.answer()
            all_links = get_all_links()
            if not all_links:
                await event.respond("لا توجد روابط محفوظة.")
                return
            txt = "🔗 كل الروابط المحفوظة:\n"
            for l in all_links:
                txt += f"• [{l.get('title')}]({l.get('link')}) — owner: {l.get('owner')}\n"
            await event.respond(txt)
            return

    # ============ USER ACTIONS ============
    if data == b"add_link":
        await event.answer()
        async with bot_client.conversation(user_id) as conv:
            await conv.send_message("📎 أرسل رابط الكروب أو الـ username (مثل t.me/xxx أو @groupname):")
            r1 = await conv.get_response()
            link = r1.text.strip()
            await conv.send_message("✍️ عطينا اسم للكروب (مثال: بيع وشراء):")
            r2 = await conv.get_response()
            title = r2.text.strip()
            # حاول استخراج ID إن كان صيغة -100... أو رقم أو username
            group_id = link  # للبساطة نخزن الرابط كما هو
            add_group_link(user_id, group_id, title, link)
            save_log_entry({"user_id": user_id, "operation": "add_link", "details": f"{title} - {link}", "timestamp": datetime.now().isoformat()})
            await conv.send_message("✅ تمت حفظ الرابط! تقدر تطلب إرسالها للقناة أو استخراجها.")
        return

    if data == b"send_links_channel":
        await event.answer()
        links = get_user_links(user_id)
        if not links:
            await event.respond("❌ ماله روابط محفوظة عندك.")
            return
        txt = f"🔗 روابط الكروبات للمستخدم [{user_id}](tg://user?id={user_id}):\n"
        for l in links:
            txt += f"• [{l.get('title')}]({l.get('link')})\n"
        try:
            await bot_client.send_message(GROUP_LINK_CHANNEL, txt)
            save_log_entry({"user_id": user_id, "operation": "send_links_channel", "details": f"{len(links)} links", "timestamp": datetime.now().isoformat()})
            await event.respond("✅ تم إرسال روابطك للقناة.")
        except Exception as e:
            await event.respond(f"❌ خطأ بإرسال الروابط للقناة: {e}")
        return

    if data == b"get_links":
        await event.answer()
        links = get_user_links(user_id)
        if not links:
            await event.respond("❌ ما عندك روابط محفوظة.")
            return
        txt = "🔗 روابطك:\n"
        for l in links:
            txt += f"• [{l.get('title')}]({l.get('link')})\n"
        await event.respond(txt)
        return

    if data == b"leave_groups":
        await event.answer()
        links = get_user_links(user_id)
        if not links:
            await event.respond("❌ ما عندك مجموعات مخزنة.")
            return
        left = 0
        errors = 0
        for l in links:
            link = l.get("link")
            try:
                # نحاول نحل الـ peer من رابط/يوزرنيم
                peer = None
                if link.startswith("t.me/"):
                    peer = link.split("t.me/")[-1]
                    if peer.startswith("+"):
                        peer = peer  # نخلّيه كما هو
                elif link.startswith("@"):
                    peer = link
                else:
                    peer = link
                # حاول نركّع الطلب; البوت ما راح يقدر يترك لو مو عضو أو لو الرابط ما صحيح
                try:
                    await bot_client(functions.messages.LeaveChatRequest(peer))
                    left += 1
                except Exception:
                    # حاول بالـ entity إن كان username أو id
                    try:
                        ent = await bot_client.get_entity(peer)
                        await bot_client(functions.messages.LeaveChatRequest(ent))
                        left += 1
                    except Exception:
                        errors += 1
            except Exception:
                errors += 1
        save_log_entry({"user_id": user_id, "operation": "leave_groups", "details": f"left={left}, errs={errors}", "timestamp": datetime.now().isoformat()})
        await event.respond(f"✅ انتهى! خرجت من {left} مجموعات. أخطاء: {errors}")
        return

    if data == b"speed_setting":
        await event.answer()
        settings = get_user_settings(user_id)
        async with bot_client.conversation(user_id) as conv:
            await conv.send_message(f"⏱️ التأخير الحالي بين عمليات 'الإنشاء' (محاكى) هو: {settings['delay_between_groups']} ثانية.\nأدخل قيمة جديدة بالثواني:")
            r = await conv.get_response()
            try:
                v = int(r.text.strip())
                set_user_setting(user_id, "delay_between_groups", v)
                await conv.send_message(f"✅ تم تحديث التأخير إلى {v} ثانية.")
            except:
                await conv.send_message("❌ ادخل رقم صحيح.")
        return

    if data == b"create_groups":
        # توضيح: البوت (token) ما يقدر ينشئ مجموعات بنفسه
        await event.answer()
        msg = ("⚠️ ملاحظة مهمة: البوت لا يستطيع إنشاء مجموعات بنفسه عبر الـ Bot Token.\n"
               "البدائل:\n"
               "1) استعمل حساب User (userbot) لإنشاء مجموعات — هذا يتطلب رقم هاتف وجلسة.\n"
               "2) أنشئ المجموعات يدوياً ثم أرسِل لي الروابط لأحفظها أو أنشرها.\n\n"
               "أريد أساعدك سريع — تفضل أحد الخيارين أعلاه وانا أتابع.")
        await event.respond(msg)
        return

# ---------- تشغيل البوت ----------
async def main():
    await bot_client.start(bot_token=BOT_TOKEN)
    print("[*] بوت التلي شغّال — ارسل /start")
    await bot_client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
