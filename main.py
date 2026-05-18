import telebot
import random
import time
import json
import os
import re
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot import apihelper

# --- الإعدادات الأساسية ---
API_TOKEN = "8226554216:AAGNrdE1XH3E_PRFp31HlDK4nj7gqmWghuU"
bot = telebot.TeleBot(API_TOKEN, threaded=True, num_threads=8)

def safe_edit(chat_id, message_id, text, reply_markup=None, parse_mode=None):
    try:
        bot.edit_message_text(
            text, chat_id, message_id,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise

# --- قائمة المطورين والملفات ---
MAIN_DEV = 6312222592
developers_file = "developers.json"
points_file = "user_points.json"
gangs_file = "gangs.json"
banned_tops_file = "banned_tops.json"
banned_users_file = "banned_users.json"
sentences_file = "sentences.json"
bot_status = True
allowed_groups = set()
allowed_users = set()

# --- إعدادات الاشتراك الإجباري ---
REQUIRED_CHANNEL = "@Bot_F_Fast"

def is_subscribed(uid):
    try:
        member = bot.get_chat_member(REQUIRED_CHANNEL, uid)
        return member.status not in ["left", "kicked", "banned"]
    except:
        return True

# --- قفل لحماية البيانات عند الكتابة المتزامنة ---
data_lock = threading.Lock()
_data_dirty = False

# --- دوال إدارة البيانات ---
def load_json(file, default):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return default
    return default

def save_json(file, data):
    tmp = file + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, file)

def mark_dirty():
    global _data_dirty
    _data_dirty = True

# تحميل البيانات
user_points = load_json(points_file, {})
gangs = load_json(gangs_file, {})
groups_file = "groups_data.json"
groups_data = load_json(groups_file, {})

# تحميل المطورين من الملف (المطور الأصلي دائماً موجود)
_devs_raw = load_json(developers_file, [MAIN_DEV])
developers = list(set([MAIN_DEV] + [int(x) for x in _devs_raw]))

# تحميل قوائم الحظر
banned_tops = set(str(x) for x in load_json(banned_tops_file, []))
banned_users = set(str(x) for x in load_json(banned_users_file, []))

# --- فهرس سريع: acc_id → uid ---
acc_index = {str(data["acc_id"]): uid for uid, data in user_points.items() if data.get("acc_id")}

# --- فهرس سريع: uid → gang_name ---
uid_to_gang = {}
for gname, gdata in gangs.items():
    for mid in gdata.get("members", []):
        uid_to_gang[mid] = gname

# --- نظام الحفظ التلقائي ---
def auto_save_loop():
    global _data_dirty
    while True:
        time.sleep(30)
        if _data_dirty:
            with data_lock:
                save_json(points_file, user_points)
                save_json(gangs_file, gangs)
                save_json(groups_file, groups_data)
                save_json(developers_file, developers)
                save_json(banned_tops_file, list(banned_tops))
                save_json(banned_users_file, list(banned_users))
                save_json(sentences_file, sentences_list)
                _data_dirty = False

threading.Thread(target=auto_save_loop, daemon=True).start()

# --- دوال التنسيق والمعالجة ---
def format_num(num):
    arabic_digits = "𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿"
    num_str = f"{num:,}"
    result = ""
    for char in num_str:
        if char.isdigit():
            result += arabic_digits[int(char)]
        else:
            result += char
    return result

def normalize_text(text, game_type=None):
    if not text:
        return ""
    if game_type in ("ر", "ت", "نت", "م"):
        return "".join(filter(str.isdigit, text))
    text = text.strip()
    text = text.replace("ة", "ه").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    return re.sub(r'[^\w]', '', text)

def get_user_data(uid, name="لاعب"):
    uid_s = str(uid)
    if uid_s not in user_points:
        user_points[uid_s] = {}
    data = user_points[uid_s]
    defaults = {
        "pts": 0, "total_pts": 0, "best_time": 999.0, "name": name,
        "acc_id": None, "last_salary": 0, "last_rob": 0, "last_invest": 0,
        "last_trade": 0, "last_luck": 0, "last_tip": 0,
        "bank_type": "⚡ بنك لاعبين الاسرع", "card_type": "ماستر كارد",
        "best_val_net": "0", "best_time_net": 999.0,
        "best_val_k": "لا يوجد", "best_time_k": 999.0,
        "best_val_m": "0", "best_time_m": 999.0,
        "best_val_f": "لا يوجد", "best_time_f": 999.0,
        "best_val_r": "0", "best_time_r": 999.0,
        "best_val_j": "لا يوجد", "best_time_j": 999.0
    }
    for key, value in defaults.items():
        if key not in data:
            data[key] = value
    return data

def get_rank_title(dt):
    if dt <= 0.50: return "🥇 أسطوري"
    elif dt <= 1.00: return "🥈 فضي"
    elif dt <= 1.50: return "🥉 برونزي"
    elif dt <= 2.50: return "🎖️ محترف"
    else: return "👤 لاعب"

# --- قائمة الكلمات ---
words_list = [
    "بيت", "بحر", "شمس", "قمر", "نهر", "جبل", "ورد", "نار",
    "مطر", "غيم", "باب", "مفتاح", "كتاب", "قلم", "دفتر",
    "مدرسة", "شارع", "سيارة", "طيارة", "قطار", "كرسي",
    "طاولة", "نافذة", "صورة", "ساعة", "هاتف", "سماعة",
    "شاشة", "كمبيوتر", "انترنت", "لعبة", "كرة", "ملعب",
    "جمهور", "ضحك", "حزن", "فرح", "حلم", "نوم", "صباح",
    "مساء", "ليل", "نهار", "قهوة", "شاي", "عصير", "تفاح",
    "برتقال", "موز", "عنب", "خبز", "رز", "لحم", "دجاج",
    "سمك", "صديق", "حبيب", "اخ", "اخت", "ام", "اب",
    "طفل", "رجل", "امرأة", "مدينة", "قرية", "دولة", "علم",
    "جيش", "شرطة", "مستشفى", "دكتور", "ممرض", "دواء",
    "صحة", "مرض", "رياضة", "سباحة", "جري", "دراسة",
    "نجاح", "فشل", "امتحان", "جامعة", "وظيفة", "راتب",
    "فلوس", "بنك", "تجارة", "سوق", "ذهب", "فضة",
    "الماس", "حجر", "خشب", "حديد", "ماء", "هواء",
    "تراب", "كهرباء", "طاقة", "سفر", "مطار", "حقيبة",
    "فندق", "جزيرة", "غابة", "اسد", "نمر", "ذئب",
    "ثعلب", "قطة", "كلب", "طير", "نسر", "حمامة",
    "سمكة", "حوت", "دولفين", "وردة", "شجرة", "زهرة",
    "عشب", "صحراء", "ثلج", "برد", "حر", "صيف",
    "شتاء", "ربيع", "خريف", "دقيقة", "ثانية", "سنة",
    "شهر", "اسبوع", "يوم", "ضوء", "ظلام", "لون"
]

# --- قائمة الجمل (لعبة ج) ---
sentences_list = [
    "الجو اليوم جميل جداً",
    "أحب اللعب مع الأصدقاء",
    "الماء أساس الحياة",
    "العلم نور والجهل ظلام",
    "الصبر مفتاح الفرج",
    "البيت الجميل بيت السعادة",
    "الأم حنانها لا يعوض",
    "السفر يوسع الأفق",
    "الكتاب أفضل صديق",
    "الرياضة تقوي الجسم",
    "الوقت من ذهب",
    "النوم مبكراً مفيد للصحة",
    "الطعام الصحي ضروري",
    "المدرسة بيت العلم",
    "الشمس تشرق من الشرق",
    "البحر عميق وجميل",
    "الطيور تغني في الصباح",
    "اللعب مع الأصدقاء ممتع",
    "الحياة جميلة ومليئة بالأمل",
    "الفوز يحتاج صبر وتعب",
    "الشجرة تنمو ببطء",
    "المطر ينزل في الشتاء",
    "القمر يضيء الليل",
    "الأسرة هي كل شيء",
    "العمل الجاد يأتي بالنجاح",
    "الكرة الجميلة في الملعب",
    "الجبل الشامخ يلمس السحاب",
    "الذهب يلمع في الشمس",
    "الطفل يلعب بفرح",
    "القهوة مشروب الصباح",
]

# تحميل الجمل المحفوظة وإضافتها للقائمة
_saved_sentences = load_json(sentences_file, [])
for _s in _saved_sentences:
    if _s not in sentences_list:
        sentences_list.append(_s)

# ============================================================
# 🛡️ نظام العصابات
# ============================================================

GANG_COST = 20000
GANG_MAX_MEMBERS = 10
WAR_TIMEOUT = 30

gang_wars = {}


def get_user_gang(uid):
    uid_s = str(uid)
    gang_name = uid_to_gang.get(uid_s)
    if gang_name and gang_name in gangs:
        return gang_name, gangs[gang_name]
    return None, None


def gang_total_points(gdata):
    return sum(user_points.get(uid, {}).get("total_pts", 0) for uid in gdata.get("members", []))


# 🔴 فحص الحظر النهائي - قبل أي handler آخر
@bot.message_handler(func=lambda m: str(m.from_user.id) in banned_users and m.from_user.id not in developers)
def handle_banned_user(message):
    bot.reply_to(message, "🔴 أنت محظور من استخدام هذا البوت.")


# كلمات وأوامر البوت التي تستوجب الاشتراك
_BOT_TRIGGERS = {
    "ك", "ف", "ر", "ت", "نت", "م", "كمله", "ج",
    "اح", "حسابي", "فلوسي", "بخشيش", "راتب", "زرف",
    "توب الفلوس", "توب النقاط", "توب القياسي", "توب النت",
    "توب ك", "توب م", "توب ف", "توب ر", "توب ج", "توب الكروبات",
    "توب العصابات", "انشاء عصابة", "مغادرة عصابة", "عصابتي",
    "حذف عصابة", "القاتل", "بدأ", "إيقاف القاتل",
    "انشاء حساب بنكي", "مسح حساب بنكي",
}

def _is_bot_command(m):
    if not m.text:
        return False
    txt = m.text.strip()
    if txt.startswith("/"):
        return True
    if txt in _BOT_TRIGGERS:
        return True
    for prefix in ("انضمام عصابة", "نقل قيادة", "حرب عصابات",
                   "حظ ", "مضاربه ", "استثمار ", "تحويل ",
                   "اقترح جمله"):
        if txt.startswith(prefix):
            return True
    return False


# 🔒 فحص الاشتراك الإجباري — يعمل فقط عند استخدام أوامر البوت
@bot.message_handler(func=lambda m: m.from_user.id not in developers and str(m.from_user.id) not in banned_users and not is_subscribed(m.from_user.id) and _is_bot_command(m))
def require_subscription(message):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📢 اشترك في القناة", url="https://t.me/Bot_F_Fast"),
        InlineKeyboardButton("✅ تحققت من الاشتراك", callback_data="check_sub")
    )
    bot.reply_to(
        message,
        "⚠️ يجب عليك الاشتراك في قناتنا أولاً!\n\n"
        "📢 اضغط على الزر للاشتراك، ثم اضغط ✅ تحققت من الاشتراك",
        reply_markup=markup
    )


@bot.message_handler(func=lambda m: m.text == "انشاء عصابة")
def create_gang(message):
    uid = str(message.from_user.id)
    user = get_user_data(uid, message.from_user.first_name)

    if not user.get("acc_id"):
        return bot.reply_to(message, "❌ تحتاج حساب بنكي أولاً!")

    existing_gang, _ = get_user_gang(uid)
    if existing_gang:
        return bot.reply_to(message, f"❌ أنت بالفعل عضو في عصابة: {existing_gang}")

    if user["pts"] < GANG_COST:
        return bot.reply_to(message, f"❌ تحتاج {format_num(GANG_COST)} دينار لإنشاء عصابة!\n⇜ رصيدك: {format_num(user['pts'])} دينار")

    bot.reply_to(message, "✏️ أرسل اسم العصابة (2-20 حرف):")
    bot.register_next_step_handler(message, process_gang_name, uid, user)


def process_gang_name(message, uid, user):
    name = message.text.strip()

    if len(name) < 2 or len(name) > 20:
        return bot.reply_to(message, "❌ الاسم يجب أن يكون 2-20 حرف!")

    if name in gangs:
        return bot.reply_to(message, "❌ هذا الاسم مأخوذ! اختر اسماً آخر.")

    with data_lock:
        user["pts"] -= GANG_COST
        gangs[name] = {
            "leader": uid,
            "members": [uid],
            "created_at": time.time(),
            "wins": 0,
            "losses": 0
        }
        uid_to_gang[uid] = name
        mark_dirty()

    bot.reply_to(
        message,
        f"🛡️ تم إنشاء عصابة [{name}] بنجاح!\n"
        f"⇜ القائد: {user['name']}\n"
        f"⇜ التكلفة: {format_num(GANG_COST)} دينار\n"
        f"⇜ الأعضاء: 1/{GANG_MAX_MEMBERS}\n\n"
        f"📢 للانضمام: انضمام عصابة {name}"
    )


@bot.message_handler(func=lambda m: m.text and m.text.startswith("انضمام عصابة"))
def join_gang(message):
    uid = str(message.from_user.id)
    user = get_user_data(uid, message.from_user.first_name)

    if not user.get("acc_id"):
        return bot.reply_to(message, "❌ تحتاج حساب بنكي أولاً!")

    existing_gang, _ = get_user_gang(uid)
    if existing_gang:
        return bot.reply_to(message, f"❌ أنت بالفعل في عصابة: {existing_gang}")

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        return bot.reply_to(message, "📋 الصيغة: انضمام عصابة (الاسم)")

    gang_name = parts[2].strip()
    if gang_name not in gangs:
        return bot.reply_to(message, "❌ العصابة غير موجودة!")

    gdata = gangs[gang_name]
    if len(gdata["members"]) >= GANG_MAX_MEMBERS:
        return bot.reply_to(message, f"❌ العصابة ممتلئة! (الحد {GANG_MAX_MEMBERS} أعضاء)")

    with data_lock:
        gdata["members"].append(uid)
        uid_to_gang[uid] = gang_name
        mark_dirty()

    leader_name = user_points.get(gdata["leader"], {}).get("name", "مجهول")
    bot.reply_to(
        message,
        f"✅ انضممت لعصابة [{gang_name}] بنجاح!\n"
        f"⇜ القائد: {leader_name}\n"
        f"⇜ الأعضاء: {len(gdata['members'])}/{GANG_MAX_MEMBERS}"
    )


@bot.message_handler(func=lambda m: m.text == "مغادرة عصابة")
def leave_gang(message):
    uid = str(message.from_user.id)
    gang_name, gdata = get_user_gang(uid)

    if not gang_name:
        return bot.reply_to(message, "❌ أنت لست في أي عصابة!")

    if gdata["leader"] == uid:
        return bot.reply_to(message, "❌ أنت القائد! نقّل القيادة أولاً أو احذف العصابة.\nالأوامر: نقل قيادة | حذف عصابة")

    with data_lock:
        gdata["members"].remove(uid)
        uid_to_gang.pop(uid, None)
        mark_dirty()

    bot.reply_to(message, f"✅ غادرت عصابة [{gang_name}] بنجاح.")


@bot.message_handler(func=lambda m: m.text == "حذف عصابة")
def delete_gang(message):
    uid = str(message.from_user.id)
    gang_name, gdata = get_user_gang(uid)

    if not gang_name or gdata["leader"] != uid:
        return bot.reply_to(message, "❌ أنت لست قائد أي عصابة!")

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ نعم، احذف", callback_data=f"delgang_{gang_name}"),
        InlineKeyboardButton("❌ تراجع", callback_data="delgang_no")
    )
    bot.reply_to(message, f"⚠️ هل تريد حذف عصابة [{gang_name}] نهائياً؟", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("delgang_"))
def handle_delete_gang(call):
    uid = str(call.from_user.id)
    if call.data == "delgang_no":
        return safe_edit(call.message.chat.id, call.message.message_id, "❌ تم إلغاء الحذف.")

    gang_name = call.data[8:]
    if gang_name in gangs and gangs[gang_name]["leader"] == uid:
        with data_lock:
            for mid in gangs[gang_name].get("members", []):
                uid_to_gang.pop(mid, None)
            del gangs[gang_name]
            mark_dirty()
        safe_edit(call.message.chat.id, call.message.message_id, f"✅ تم حذف عصابة [{gang_name}] نهائياً.")
    else:
        safe_edit(call.message.chat.id, call.message.message_id, "❌ حدث خطأ!")


@bot.message_handler(func=lambda m: m.text and m.text.startswith("نقل قيادة"))
def transfer_leadership(message):
    uid = str(message.from_user.id)
    gang_name, gdata = get_user_gang(uid)

    if not gang_name or gdata["leader"] != uid:
        return bot.reply_to(message, "❌ أنت لست قائد أي عصابة!")

    if not message.reply_to_message:
        return bot.reply_to(message, "↩️ رد على رسالة العضو الذي تريد نقل القيادة إليه!")

    target_uid = str(message.reply_to_message.from_user.id)
    if target_uid not in gdata["members"]:
        return bot.reply_to(message, "❌ هذا الشخص ليس في عصابتك!")

    with data_lock:
        gdata["leader"] = target_uid
        mark_dirty()

    target_name = user_points.get(target_uid, {}).get("name", "مجهول")
    bot.reply_to(message, f"✅ تم نقل القيادة إلى [{target_name}] بنجاح!")


@bot.message_handler(func=lambda m: m.text == "عصابتي")
def my_gang(message):
    uid = str(message.from_user.id)
    gang_name, gdata = get_user_gang(uid)

    if not gang_name:
        return bot.reply_to(message, "❌ أنت لست في أي عصابة!\nأرسل: انشاء عصابة أو انضمام عصابة (الاسم)")

    leader_name = user_points.get(gdata["leader"], {}).get("name", "مجهول")
    total_pts = gang_total_points(gdata)

    members_text = ""
    for i, mid in enumerate(gdata["members"], 1):
        mdata = user_points.get(mid, {})
        icon = "👑" if mid == gdata["leader"] else f"{i}."
        members_text += f"{icon} {mdata.get('name', 'مجهول')} ← {format_num(mdata.get('total_pts', 0))} نقطة\n"

    res = (
        f"🛡️ عصابة [{gang_name}]\n\n"
        f"👑 القائد: {leader_name}\n"
        f"👥 الأعضاء: {len(gdata['members'])}/{GANG_MAX_MEMBERS}\n"
        f"🏅 مجموع النقاط: {format_num(total_pts)}\n"
        f"⚔️ انتصارات: {gdata.get('wins', 0)} | خسائر: {gdata.get('losses', 0)}\n\n"
        f"قائمة الأعضاء:\n{members_text}\n༄"
    )
    bot.reply_to(message, res)


@bot.message_handler(func=lambda m: m.text == "توب العصابات")
def gang_top(message):
    if not gangs:
        return bot.reply_to(message, "⚠️ لا توجد عصابات حالياً!")

    sorted_gangs = sorted(gangs.items(), key=lambda x: gang_total_points(x[1]), reverse=True)[:10]
    icons = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    res = "🏆 توب العصابات\n\n"
    for i, (gname, gdata) in enumerate(sorted_gangs):
        leader_name = user_points.get(gdata["leader"], {}).get("name", "مجهول")
        total = gang_total_points(gdata)
        res += (
            f"{icons[i]} [{gname}]\n"
            f"   👑 {leader_name} | 👥 {len(gdata['members'])} عضو | 🏅 {format_num(total)} نقطة\n\n"
        )
    bot.reply_to(message, res + "༄")


# ============================================================
# ⚔️ حروب العصابات
# ============================================================

gang_pending = {}

ROUND_TIMEOUT = 20
TOTAL_ROUNDS  = 6


def build_rounds():
    rounds = []
    for _ in range(3):
        rounds.append({"type": "word", "value": random.choice(words_list)})
    for _ in range(3):
        num = random.randint(100, 9999)
        rounds.append({"type": "num", "value": str(num)})
    return rounds


def next_round(cid):
    war = gang_wars.get(cid)
    if not war:
        return

    war["round_idx"] += 1
    idx = war["round_idx"]

    if idx >= TOTAL_ROUNDS:
        finish_gang_war(cid)
        return

    current = war["rounds"][idx]
    war["round_winner"] = None
    war["answered_this_round"] = set()
    war["round_start"] = time.time()

    rtype = "📝 كلمة" if current["type"] == "word" else "🔢 رقم"
    bot.send_message(
        cid,
        f"⚔️ الجولة {idx + 1}/{TOTAL_ROUNDS} | {rtype}\n\n"
        f"اكتب: {current['value']}\n"
        f"⏱️ عندكم {ROUND_TIMEOUT} ثانية!"
    )

    def round_timeout():
        time.sleep(ROUND_TIMEOUT)
        w = gang_wars.get(cid)
        if w and w["round_idx"] == idx and w.get("round_winner") is None:
            bot.send_message(cid, f"⏰ انتهى وقت الجولة {idx + 1}! لا أحد فاز بهذه الجولة.")
            next_round(cid)

    threading.Thread(target=round_timeout, daemon=True).start()


@bot.message_handler(func=lambda m: m.text and m.text.startswith("حرب عصابات"))
def start_gang_war(message):
    uid = str(message.from_user.id)
    my_gang_name, my_gang_data = get_user_gang(uid)

    if not my_gang_name:
        return bot.reply_to(message, "❌ أنت لست في أي عصابة!")
    if my_gang_data["leader"] != uid:
        return bot.reply_to(message, "❌ فقط القائد يمكنه إعلان الحرب!")

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        return bot.reply_to(message, "📋 الصيغة: حرب عصابات (اسم العصابة المنافسة)")

    enemy_name = parts[2].strip()
    if enemy_name not in gangs:
        return bot.reply_to(message, "❌ العصابة المنافسة غير موجودة!")
    if enemy_name == my_gang_name:
        return bot.reply_to(message, "❌ لا يمكنك محاربة عصابتك!")

    cid = message.chat.id
    if cid in gang_wars:
        return bot.reply_to(message, "⚔️ يوجد حرب جارية حالياً في هذه المجموعة!")
    if cid in gang_pending:
        return bot.reply_to(message, "⏳ يوجد تحدي معلق انتظر قبوله أو رفضه!")

    enemy_leader_uid = gangs[enemy_name]["leader"]
    enemy_leader_name = user_points.get(enemy_leader_uid, {}).get("name", "مجهول")

    gang_pending[cid] = {
        "gang1": my_gang_name,
        "gang2": enemy_name,
        "challenger_uid": uid,
        "enemy_leader_uid": enemy_leader_uid,
        "time": time.time()
    }

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ قبول", callback_data=f"war_accept_{cid}"),
        InlineKeyboardButton("❌ رفض",  callback_data=f"war_reject_{cid}")
    )

    bot.reply_to(
        message,
        f"⚔️ تحدي حرب عصابات!\n\n"
        f"🛡️ [{my_gang_name}] يتحدى ⚔️ [{enemy_name}]\n\n"
        f"👑 قائد [{enemy_name}]: {enemy_leader_name}\n"
        f"⏳ عندك 60 ثانية للرد على التحدي!\n\n"
        f"📢 يا قائد [{enemy_name}] اضغط قبول أو رفض!",
        reply_markup=markup
    )

    def expire_challenge():
        time.sleep(60)
        if cid in gang_pending and gang_pending[cid].get("challenger_uid") == uid:
            gang_pending.pop(cid, None)
            bot.send_message(cid, f"⌛ انتهت صلاحية تحدي [{my_gang_name}]! لم يتم الرد.")

    threading.Thread(target=expire_challenge, daemon=True).start()


@bot.callback_query_handler(func=lambda call: call.data.startswith(("war_accept_", "war_reject_")))
def handle_war_response(call):
    uid = str(call.from_user.id)
    parts = call.data.split("_")
    action = parts[1]
    cid = int(parts[2])

    if cid not in gang_pending:
        return bot.answer_callback_query(call.id, "❌ انتهت صلاحية هذا التحدي!")

    pending = gang_pending[cid]

    if uid != pending["enemy_leader_uid"]:
        return bot.answer_callback_query(call.id, "❌ فقط قائد العصابة المتحداة يقدر يرد!")

    gang_pending.pop(cid, None)

    if action == "reject":
        safe_edit(
            call.message.chat.id, call.message.message_id,
            f"❌ رفض قائد [{pending['gang2']}] التحدي!"
        )
        return

    g1, g2 = pending["gang1"], pending["gang2"]

    if g1 not in gangs or g2 not in gangs:
        return safe_edit(call.message.chat.id, call.message.message_id, "❌ إحدى العصابتين لم تعد موجودة!")

    rounds = build_rounds()
    gang_wars[cid] = {
        "gang1": g1,
        "gang2": g2,
        "rounds": rounds,
        "round_idx": -1,
        "round_winner": None,
        "round_start": None,
        "scores": {g1: 0, g2: 0},
        "answered_this_round": set()
    }

    safe_edit(
        call.message.chat.id, call.message.message_id,
        f"✅ قبل قائد [{g2}] التحدي!\n\n"
        f"⚔️ [{g1}] VS [{g2}]\n\n"
        f"🎮 الحرب تبدأ الآن!\n"
        f"6 جولات: 3 كلمات + 3 أرقام\n"
        f"من يكتب الإجابة أول يأخذ نقطة لعصابته! 🏆"
    )

    time.sleep(2)
    next_round(cid)


def finish_gang_war(cid):
    war = gang_wars.pop(cid, None)
    if not war:
        return

    g1, g2 = war["gang1"], war["gang2"]
    s1, s2 = war["scores"].get(g1, 0), war["scores"].get(g2, 0)

    if s1 == s2:
        bot.send_message(
            cid,
            f"⚔️ نتيجة حرب العصابات\n\n"
            f"🛡️ [{g1}]: {s1} نقطة\n"
            f"⚔️ [{g2}]: {s2} نقطة\n\n"
            f"🤝 تعادل! لا يوجد فائز."
        )
        return

    winner = g1 if s1 > s2 else g2
    loser  = g2 if s1 > s2 else g1
    ws     = s1 if s1 > s2 else s2
    ls     = s2 if s1 > s2 else s1

    with data_lock:
        if winner in gangs:
            gangs[winner]["wins"] = gangs[winner].get("wins", 0) + 1
        if loser in gangs:
            gangs[loser]["losses"] = gangs[loser].get("losses", 0) + 1
        for mid in gangs.get(winner, {}).get("members", []):
            if mid in user_points:
                user_points[mid]["pts"]       = user_points[mid].get("pts", 0) + 500
                user_points[mid]["total_pts"] = user_points[mid].get("total_pts", 0) + 1
        mark_dirty()

    bot.send_message(
        cid,
        f"🏁 انتهت حرب العصابات!\n\n"
        f"🛡️ [{g1}]: {s1} نقطة\n"
        f"⚔️ [{g2}]: {s2} نقطة\n\n"
        f"🏆 الفائز: [{winner}] بـ {ws} نقاط!\n"
        f"💸 كل عضو في [{winner}] حصل على 500 دينار مكافأة!\n༄"
    )


# ============================================================
# لوحة تحكم المطورين
# ============================================================

@bot.message_handler(commands=['admin'], func=lambda m: m.from_user.id in developers)
def admin_panel(message):
    is_main = message.from_user.id == MAIN_DEV
    panel_text = (
        "━━━━━━━━━━━━━━━━━━\n"
        "🛠 **لوحة تحكم الإدارة**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "⚙️ **التفعيل الشامل:**\n"
        "• `/تفعيل_للـكل` — فتح البوت للجميع\n"
        "• `/تعطيل_للـكل` — إغلاق البوت للعموم\n\n"
        "🔧 **التفعيل اليدوي:**\n"
        "• `/addgroup ID` — تفعيل مجموعة\n"
        "• `/delgroup ID` — تعطيل مجموعة\n"
        "• `/adduser ID` — تفعيل مستخدم\n\n"
        "💾 **إدارة البيانات:**\n"
        "• `/تصفير` — مسح كل الحسابات\n"
        "• `/صفر_الكل` — تصفير فلوس الكل\n"
        "• `/صفر (الحساب)` — تصفير فلوس لاعب\n"
        "• `/نط (المبلغ) (الحساب)` — منح أموال للاعب\n\n"
        "📝 **الجمل والكلمات:**\n"
        "• `/أضف_كلمه (كلمة)` — إضافة كلمة للعبة ك\n"
        "• `/حذف_كلمه (كلمة)` — حذف كلمة من ك\n"
        "• `/أضف_جمله (جملة)` — إضافة جملة للعبة ج\n"
        "• `/حذف_جمله (جملة)` — حذف جملة من ج\n"
        "• `/عرض_الجمل` — عرض جميع جمل لعبة ج\n\n"
        "🚫 **الحظر:**\n"
        "• `/حضر_توب ID` — حظر من التوبات فقط\n"
        "• `/رفع_توب ID` — رفع حظر التوبات\n"
        "• `/حضر_كلي ID` — حظر نهائي من البوت\n"
        "• `/رفع_كلي ID` — رفع الحظر النهائي\n\n"
        "🛡️ **العصابات:**\n"
        "• `/عصابات_الكل` — عرض جميع العصابات\n"
        "• `/حذف_عصابة (الاسم)` — حذف عصابة قسراً\n\n"
        "🔄 **تصفير التوبات** _(ID أو رقم الترتيب)_:\n"
        "• `/تصفير_النت` — توب النت\n"
        "• `/تصفير_ك` — توب ك\n"
        "• `/تصفير_م` — توب م\n"
        "• `/تصفير_ف` — توب ف\n"
        "• `/تصفير_ر` — توب ر\n"
        "• `/تصفير_ج` — توب ج\n"
        "• `/تصفير_القياسي` — توب القياسي\n"
        "• `/تصفير_الفلوس` — توب الفلوس\n"
        "• `/تصفير_النقاط` — توب النقاط"
    )
    if is_main:
        panel_text += (
            "\n\n━━━━━━━━━━━━━━━━━━\n"
            "👑 **أوامر المطور الرئيسي:**\n"
            "• `/اضف_مطور ID` — إضافة مطور جديد\n"
            "• `/انزل_مطور ID` — إزالة مطور\n"
            "• `/المطورين` — عرض قائمة المطورين\n"
            "━━━━━━━━━━━━━━━━━━"
        )
    bot.reply_to(message, panel_text, parse_mode="Markdown")


@bot.message_handler(commands=['عصابات_الكل'], func=lambda m: m.from_user.id in developers)
def admin_all_gangs(message):
    if not gangs:
        return bot.reply_to(message, "لا توجد عصابات.")
    res = f"🛡️ جميع العصابات ({len(gangs)}):\n\n"
    for gname, gdata in gangs.items():
        res += f"• [{gname}] - {len(gdata['members'])} عضو - انتصارات: {gdata.get('wins',0)}\n"
    bot.reply_to(message, res)


@bot.message_handler(commands=['حذف_عصابة'], func=lambda m: m.from_user.id in developers)
def admin_delete_gang(message):
    try:
        gang_name = message.text.split(maxsplit=1)[1].strip()
        if gang_name in gangs:
            with data_lock:
                for mid in gangs[gang_name].get("members", []):
                    uid_to_gang.pop(mid, None)
                del gangs[gang_name]
                mark_dirty()
            bot.reply_to(message, f"✅ تم حذف عصابة [{gang_name}].")
        else:
            bot.reply_to(message, "❌ العصابة غير موجودة!")
    except:
        bot.reply_to(message, "📋 الصيغة: /حذف_عصابة (الاسم)")


@bot.message_handler(commands=['نط'], func=lambda m: m.from_user.id in developers)
def gift_money(message):
    try:
        parts = message.text.split()
        amount = int(parts[1])
        target_acc_id = str(parts[2])
        target_uid = acc_index.get(target_acc_id)
        if not target_uid:
            return bot.reply_to(message, "❌ رقم الحساب غير موجود!")
        with data_lock:
            user_points[target_uid]['pts'] += amount
            mark_dirty()
        bot.reply_to(message, f"✅ تم منح {format_num(amount)} دينار لـ {user_points[target_uid]['name']}")
    except:
        bot.reply_to(message, "📋 الصيغة: /نط (المبلغ) (رقم الحساب)")


@bot.message_handler(commands=['صفر_الكل'], func=lambda m: m.from_user.id in developers)
def reset_all_money_cmd(message):
    with data_lock:
        for uid in user_points:
            user_points[uid]['pts'] = 0
        mark_dirty()
    bot.reply_to(message, "✅ تم تصفير أموال جميع اللاعبين.")


@bot.message_handler(commands=['صفر'], func=lambda m: m.from_user.id in developers)
def reset_single_user_money(message):
    try:
        target_acc_id = str(message.text.split()[1])
        target_uid = acc_index.get(target_acc_id)
        if not target_uid:
            return bot.reply_to(message, "❌ رقم الحساب غير موجود!")
        with data_lock:
            user_points[target_uid]['pts'] = 0
            mark_dirty()
        bot.reply_to(message, f"✅ تم تصفير أموال {user_points[target_uid]['name']}.")
    except:
        bot.reply_to(message, "📋 الصيغة: /صفر (رقم الحساب)")


# ============================================================
# نظام التوبات
# ============================================================

_top_icons = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]


def generate_individual_top(title, suffix):
    val_field  = f"best_val_{suffix}"
    time_field = f"best_time_{suffix}"
    val_icon   = "🔤" if suffix in ["k", "f"] else "🔢"
    top_list = [(uid, data) for uid, data in user_points.items() if data.get(time_field, 999.0) < 999.0 and uid not in banned_tops]
    top_list = sorted(top_list, key=lambda x: x[1][time_field])[:5]
    if not top_list:
        return f"⚠️ لا يوجد لاعبين في {title} حالياً."
    res = f"🏆 {title}\n\n"
    for i, (uid, data) in enumerate(top_list):
        res += f"{_top_icons[i]} ❯ {data.get('name', 'لاعب')}\n"
        res += f"   ├ ⏱️ {data.get(time_field, 0)} ثانية\n"
        res += f"   └ {val_icon} {data.get(val_field, 'غير معروف')}\n\n"
    return res + "༄"


def generate_money_top(title, field, unit, limit=10):
    top_list = sorted([(uid, d) for uid, d in user_points.items() if uid not in banned_tops], key=lambda x: x[1].get(field, 0), reverse=True)[:limit]
    if not top_list:
        return f"⚠️ لا يوجد بيانات في {title} حالياً."
    res = f"🏆 {title}\n\n"
    for i, (uid, data) in enumerate(top_list):
        res += f"{_top_icons[i]} ❯ {data.get('name', 'لاعب')}\n"
        res += f"   └ 💰 {format_num(data.get(field, 0))} {unit}\n\n"
    return res + "༄"


def generate_time_top(title, limit=10):
    top_list = sorted([(uid, d) for uid, d in user_points.items() if uid not in banned_tops], key=lambda x: x[1].get('best_time', 999.0))[:limit]
    top_list = [(uid, data) for uid, data in top_list if data.get('best_time', 999.0) < 999.0]
    if not top_list:
        return f"⚠️ لا يوجد بيانات في {title} حالياً."
    res = f"🏆 {title}\n\n"
    for i, (uid, data) in enumerate(top_list):
        res += f"{_top_icons[i]} ❯ {data.get('name', 'لاعب')}\n"
        res += f"   └ ⏱️ {data.get('best_time', 0)} ثانية\n\n"
    return res + "༄"


@bot.message_handler(func=lambda m: m.text in ["توب الفلوس", "توب النقاط", "توب القياسي", "توب النت", "توب ك", "توب م", "توب ف", "توب ر", "توب ج"])
def show_tops(message):
    if not user_points:
        return bot.reply_to(message, "⚠️ لا يوجد بيانات.")
    text = message.text
    if text == "توب الفلوس":
        bot.reply_to(message, generate_money_top("توب الفلوس", "pts", "دينار"))
    elif text == "توب النقاط":
        bot.reply_to(message, generate_money_top("توب النقاط", "total_pts", "نقطة"))
    elif text == "توب القياسي":
        bot.reply_to(message, generate_time_top("توب القياسي"))
    elif text == "توب النت":
        bot.reply_to(message, generate_individual_top("توب النت", "net"))
    elif text == "توب ك":
        bot.reply_to(message, generate_individual_top("توب ك", "k"))
    elif text == "توب م":
        bot.reply_to(message, generate_individual_top("توب م", "m"))
    elif text == "توب ف":
        bot.reply_to(message, generate_individual_top("توب ف", "f"))
    elif text == "توب ر":
        bot.reply_to(message, generate_individual_top("توب ر", "r"))
    elif text == "توب ج":
        bot.reply_to(message, generate_individual_top("توب ج", "j"))


# ============================================================
# النظام البنكي
# ============================================================

@bot.message_handler(func=lambda m: m.text == "انشاء حساب بنكي")
def start_create_bank(message):
    uid = str(message.from_user.id)
    if uid in user_points and user_points[uid].get('acc_id'):
        return bot.reply_to(message, "⚠️ لديك حساب بنكي بالفعل!")
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🏦 بنك الرافدين", callback_data="setbank_الرافدين"))
    markup.row(InlineKeyboardButton("⚡ بنك لاعبين الاسرع", callback_data="setbank_الاسرع"))
    markup.row(InlineKeyboardButton("💳 بنك باي بال", callback_data="setbank_باي_بال"))
    bot.reply_to(message, "🏦 اختر البنك:", reply_markup=markup)


@bot.message_handler(func=lambda m: m.text == "مسح حساب بنكي")
def confirm_delete_bank(message):
    uid = str(message.from_user.id)
    if uid not in user_points or not user_points[uid].get('acc_id'):
        return bot.reply_to(message, "❌ ليس لديك حساب بنكي.")
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("✅ نعم، متأكد", callback_data="confirm_del_yes"),
               InlineKeyboardButton("❌ لا، تراجع", callback_data="confirm_del_no"))
    bot.reply_to(message, "⚠️ هل أنت متأكد من حذف حسابك البنكي نهائياً؟", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith(('setbank_', 'confirm_del_')))
def handle_bank_actions(call):
    uid = str(call.from_user.id)
    if call.data.startswith('setbank_'):
        bank_name = call.data.split('_', 1)[1].replace('_', ' ')
        current_data = get_user_data(uid, call.from_user.first_name)
        acc_id = random.randint(10000000, 99999999)
        with data_lock:
            current_data.update({"acc_id": acc_id, "bank_type": f"بنك {bank_name}", "card_type": "ماستر كارد"})
            user_points[uid] = current_data
            acc_index[str(acc_id)] = uid
            mark_dirty()
        safe_edit(
            call.message.chat.id, call.message.message_id,
            f"✅ تم إنشاء حسابك في بنك {bank_name} بنجاح!\n⇜ رقم حسابك: `{acc_id}`",
            parse_mode="Markdown"
        )
    elif call.data == "confirm_del_yes":
        if uid in user_points:
            old_acc = str(user_points[uid].get('acc_id', ''))
            with data_lock:
                user_points[uid]['acc_id'] = None
                acc_index.pop(old_acc, None)
                mark_dirty()
        safe_edit(call.message.chat.id, call.message.message_id, "✅ تم حذف حسابك البنكي نهائياً.")
    elif call.data == "confirm_del_no":
        safe_edit(call.message.chat.id, call.message.message_id, "❌ تم إلغاء عملية المسح.")


# ============================================================
# أوامر الإدارة العامة
# ============================================================

@bot.message_handler(commands=['تفعيل_للـكل'], func=lambda m: m.from_user.id in developers)
def enable_all(message):
    global bot_status
    bot_status = True
    bot.reply_to(message, "✅ تم فتح البوت للجميع.")


@bot.message_handler(commands=['تعطيل_للـكل'], func=lambda m: m.from_user.id in developers)
def disable_all(message):
    global bot_status
    bot_status = False
    bot.reply_to(message, "🔒 تم إرجاع البوت للوضع الخاص.")


@bot.message_handler(commands=['addgroup', 'delgroup', 'adduser'], func=lambda m: m.from_user.id in developers)
def manage_ids(message):
    try:
        cmd = message.text.split()[0]
        target = int(message.text.split()[1])
        if "addgroup" in cmd:
            allowed_groups.add(target)
            bot.reply_to(message, f"✅ تم تفعيل المجموعة: {target}")
        elif "delgroup" in cmd:
            allowed_groups.discard(target)
            bot.reply_to(message, f"✅ تم تعطيل المجموعة: {target}")
        elif "adduser" in cmd:
            allowed_users.add(target)
            bot.reply_to(message, f"✅ تم تفعيل المستخدم: {target}")
    except:
        pass


@bot.message_handler(commands=['تصفير'], func=lambda m: m.from_user.id in developers)
def reset_all_data(message):
    global user_points
    with data_lock:
        user_points = {}
        acc_index.clear()
        mark_dirty()
    bot.reply_to(message, "🧹 تم مسح كل بيانات المستخدمين.")


# ============================================================
# 🔄 أوامر تصفير التوبات الفردية
# الصيغة: /تصفير_النت ID  أو  /تصفير_النت 1 (رقم الترتيب)
# ============================================================

# خريطة أنواع التوبات
_TOP_RESET_MAP = {
    "تصفير_النت":     ("net", "best_val_net",  "0",        "best_time_net",  999.0, "توب النت"),
    "تصفير_ك":        ("k",   "best_val_k",    "لا يوجد",  "best_time_k",    999.0, "توب ك"),
    "تصفير_م":        ("m",   "best_val_m",    "0",        "best_time_m",    999.0, "توب م"),
    "تصفير_ف":        ("f",   "best_val_f",    "لا يوجد",  "best_time_f",    999.0, "توب ف"),
    "تصفير_ر":        ("r",   "best_val_r",    "0",        "best_time_r",    999.0, "توب ر"),
    "تصفير_ج":        ("j",   "best_val_j",    "لا يوجد",  "best_time_j",    999.0, "توب ج"),
    "تصفير_القياسي":  (None,  None,            None,       "best_time",      999.0, "توب القياسي"),
    "تصفير_الفلوس":   (None,  "pts",           0,          None,             None,  "توب الفلوس"),
    "تصفير_النقاط":   (None,  "total_pts",     0,          None,             None,  "توب النقاط"),
}


def _get_top_sorted(suffix, time_field, val_field=None):
    """يرجع قائمة مرتبة حسب نوع التوب"""
    if suffix:
        lst = [(uid, d) for uid, d in user_points.items()
               if d.get(time_field, 999.0) < 999.0]
        return sorted(lst, key=lambda x: x[1].get(time_field, 999.0))
    elif val_field == "pts":
        return sorted(user_points.items(), key=lambda x: x[1].get("pts", 0), reverse=True)
    elif val_field == "total_pts":
        return sorted(user_points.items(), key=lambda x: x[1].get("total_pts", 0), reverse=True)
    else:
        lst = [(uid, d) for uid, d in user_points.items()
               if d.get(time_field, 999.0) < 999.0]
        return sorted(lst, key=lambda x: x[1].get(time_field, 999.0))


def _do_top_reset(message, cmd_name):
    info = _TOP_RESET_MAP.get(cmd_name)
    if not info:
        return
    suffix, val_field, val_default, time_field, time_default, top_name = info

    try:
        arg = message.text.split()[1]
    except:
        return bot.reply_to(message,
            f"📋 الصيغة:\n"
            f"/{cmd_name} ID — عن طريق الايدي\n"
            f"/{cmd_name} 1 — عن طريق رقم الترتيب في {top_name}")

    # تحديد: رقم ترتيب (<=10) أم ID
    try:
        num = int(arg)
    except:
        return bot.reply_to(message, "❌ أرسل رقم ID أو رقم الترتيب فقط!")

    target_uid = None
    target_name = None

    if num <= 10:
        # رقم ترتيب
        sorted_list = _get_top_sorted(suffix, time_field, val_field)
        if num < 1 or num > len(sorted_list):
            return bot.reply_to(message, f"❌ الترتيب [{num}] غير موجود في {top_name}!")
        target_uid, target_data = sorted_list[num - 1]
        target_name = target_data.get("name", target_uid)
    else:
        # ID مباشر
        target_uid = str(num)
        if target_uid not in user_points:
            return bot.reply_to(message, f"❌ المستخدم [{num}] غير موجود!")
        target_name = user_points[target_uid].get("name", target_uid)

    # تصفير البيانات
    with data_lock:
        if val_field and val_default is not None:
            user_points[target_uid][val_field] = val_default
        if time_field and time_default is not None:
            user_points[target_uid][time_field] = time_default
        mark_dirty()

    bot.reply_to(message,
        f"✅ تم تصفير {top_name} للاعب [{target_name}] بنجاح!")


@bot.message_handler(
    commands=list(_TOP_RESET_MAP.keys()),
    func=lambda m: m.from_user.id in developers
)
def handle_top_reset(message):
    cmd = message.text.split()[0].lstrip("/").split("@")[0]
    _do_top_reset(message, cmd)


# ============================================================
# ✅ أوامر إضافة وحذف الكلمات (مُصلحة)
# الآن تعمل كأوامر slash مطابقة للوحة التحكم
# ============================================================

@bot.message_handler(commands=['أضف_كلمه'], func=lambda m: m.from_user.id in developers)
def add_word(message):
    try:
        word = message.text.split(maxsplit=1)[1].strip()
        if word in words_list:
            return bot.reply_to(message, f"⚠️ الكلمة [{word}] موجودة أصلاً!")
        words_list.append(word)
        bot.reply_to(message, f"✅ تمت إضافة كلمة [{word}] — المجموع: {len(words_list)} كلمة")
    except:
        bot.reply_to(message, "📋 الصيغة: /أضف_كلمه (الكلمة)")


@bot.message_handler(commands=['حذف_كلمه'], func=lambda m: m.from_user.id in developers)
def remove_word(message):
    try:
        word = message.text.split(maxsplit=1)[1].strip()
        if word not in words_list:
            return bot.reply_to(message, f"❌ الكلمة [{word}] غير موجودة!")
        words_list.remove(word)
        bot.reply_to(message, f"✅ تم حذف كلمة [{word}] — المجموع: {len(words_list)} كلمة")
    except:
        bot.reply_to(message, "📋 الصيغة: /حذف_كلمه (الكلمة)")


# ============================================================
# /start — القائمة الرئيسية
# ============================================================

@bot.message_handler(commands=['start'])
def start_cmd(message):
    name = message.from_user.first_name
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🎮 الألعاب", callback_data="guide_games"))
    markup.row(InlineKeyboardButton("🏦 البنك", callback_data="guide_bank"))
    markup.row(
        InlineKeyboardButton("🏆 التوبات", callback_data="guide_tops"),
        InlineKeyboardButton("🛡️ العصابات", callback_data="guide_gangs")
    )
    markup.row(InlineKeyboardButton("🔪 لعبة القاتل", callback_data="guide_killer"))
    bot.send_message(
        message.chat.id,
        f"👋 أهلاً {name}!\n\n"
        f"مرحباً بك في البوت 🎮\n"
        f"اختر قسماً لتعرف كيف تلعب:",
        reply_markup=markup
    )


# ✅ دالة مساعدة لبناء القائمة الرئيسية (تُستخدم في start وفي الرجوع)
def build_main_guide_markup():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🎮 الألعاب", callback_data="guide_games"))
    markup.row(InlineKeyboardButton("🏦 البنك", callback_data="guide_bank"))
    markup.row(
        InlineKeyboardButton("🏆 التوبات", callback_data="guide_tops"),
        InlineKeyboardButton("🛡️ العصابات", callback_data="guide_gangs")
    )
    return markup


@bot.callback_query_handler(func=lambda call: call.data.startswith("guide_"))
def handle_guide(call):
    section = call.data[6:]  # بعد "guide_"

    # ✅ إصلاح زر الرجوع: كان يُلتقط هنا ويُتجاهل
    if section == "back":
        name = call.from_user.first_name
        safe_edit(
            call.message.chat.id,
            call.message.message_id,
            f"👋 أهلاً {name}!\n\n"
            f"مرحباً بك في البوت 🎮\n"
            f"اختر قسماً لتعرف كيف تلعب:",
            reply_markup=build_main_guide_markup()
        )
        return

    if section == "games":
        text = (
            "🎮 دليل الألعاب\n\n"
            "⚡ الألعاب المتاحة:\n\n"
            "🔤 ك — اكتب الكلمة بأسرع وقت\n"
            "   مثال: البوت يرسل (بيت) وأنت تكتب: بيت\n\n"
            "🧩 ف — فكك الكلمة وأضف مسافات بين الحروف\n"
            "   مثال: البوت يرسل (بيت) وأنت تكتب: ب ي ت\n\n"
            "💯 ر — اكتب الرقم الملياري بأسرع وقت\n"
            "   مثال: البوت يرسل (١٢٣٤٥٦٧٨٩) وأنت تكتب: 123456789\n\n"
            "🌐 نت — اكتب الرقم المكون من رقمين\n"
            "   مثال: البوت يرسل (٤٧) وأنت تكتب: 47\n\n"
            "🔢 م — اكتب الرقم المئاتي\n"
            "   مثال: البوت يرسل (٣٥٦) وأنت تكتب: 356\n\n"
            "🏅 كل إجابة صحيحة = نقطة + 50 دينار\n"
            "⏱️ كلما كنت أسرع كلما ارتفع رتبتك!"
        )
    elif section == "bank":
        text = (
            "🏦 دليل البنك\n\n"
            "📋 الأوامر المتاحة:\n\n"
            "🏦 انشاء حساب بنكي\n"
            "   أنشئ حسابك واختر بنكك\n\n"
            "💸 فلوسي\n"
            "   شوف رصيدك الحالي\n\n"
            "📊 حسابي\n"
            "   كل تفاصيل حسابك (البنك، الرصيد، النقاط...)\n\n"
            "📩 راتب\n"
            "   احصل على 2,200 دينار كل 15 دقيقة\n\n"
            "🎁 بخشيش\n"
            "   احصل على مبلغ عشوائي كل 5 دقائق\n\n"
            "🎰 حظ (المبلغ)\n"
            "   راهن على مبلغ، إما تربح أو تخسر!\n\n"
            "📈 مضاربه (المبلغ)\n"
            "   استثمر بنسبة ربح أو خسارة عشوائية\n\n"
            "💹 استثمار (المبلغ)\n"
            "   ربح مضمون 1-15% كل 15 دقيقة\n\n"
            "⚔️ زرف\n"
            "   رد على رسالة شخص لتسرق 10% من فلوسه\n\n"
            "💳 تحويل (المبلغ) الى (رقم الحساب)\n"
            "   حول فلوس لشخص ثاني"
        )
    elif section == "tops":
        text = (
            "🏆 دليل التوبات\n\n"
            "📋 الأوامر المتاحة:\n\n"
            "💸 توب الفلوس\n"
            "   أغنى 10 لاعبين بالدينار\n\n"
            "🏅 توب النقاط\n"
            "   أكثر 10 لاعبين نقاطاً\n\n"
            "⚡ توب القياسي\n"
            "   أسرع 10 لاعبين عموماً\n\n"
            "🌐 توب النت\n"
            "   أسرع 5 لاعبين في لعبة النت\n\n"
            "🔤 توب ك\n"
            "   أسرع 5 لاعبين في لعبة الكلمات\n\n"
            "🔢 توب م\n"
            "   أسرع 5 لاعبين في لعبة المئاتي\n\n"
            "🧩 توب ف\n"
            "   أسرع 5 لاعبين في لعبة التفكيك\n\n"
            "💯 توب ر\n"
            "   أسرع 5 لاعبين في لعبة الملياري\n\n"
            "🛡️ توب العصابات\n"
            "   أقوى 10 عصابات حسب مجموع النقاط"
        )
    elif section == "gangs":
        text = (
            "🛡️ دليل العصابات\n\n"
            "📋 كيف تبدأ:\n\n"
            "1️⃣ انشاء عصابة\n"
            "   أنشئ عصابتك بـ 20,000 دينار\n"
            "   (تحتاج حساب بنكي أولاً)\n\n"
            "2️⃣ انضمام عصابة (الاسم)\n"
            "   انضم لعصابة موجودة مجاناً\n\n"
            "📋 أوامر العصابة:\n\n"
            "🛡️ عصابتي\n"
            "   شوف تفاصيل عصابتك وأعضاؤها\n\n"
            "🚪 مغادرة عصابة\n"
            "   اترك عصابتك (للأعضاء فقط)\n\n"
            "👑 نقل قيادة\n"
            "   رد على رسالة عضو لتنقل له القيادة\n\n"
            "🗑️ حذف عصابة\n"
            "   احذف عصابتك نهائياً (للقائد فقط)\n\n"
            "⚔️ حرب عصابات (الاسم)\n"
            "   تحدى عصابة أخرى!\n\n"
            "🎮 كيف تجري الحرب:\n"
            "   • القائد يعلن الحرب\n"
            "   • قائد العدو يقبل أو يرفض\n"
            "   • 6 جولات: 3 كلمات + 3 أرقام\n"
            "   • من يكتب أول يأخذ نقطة لعصابته\n"
            "   • الفائز يأخذ 500 دينار لكل عضو! 🏆"
        )
    elif section == "killer":
        text = (
            "🔪 لعبة القاتل\n\n"
            "👥 الأدوار السرية:\n"
            "🔪 القاتل — يقتل لاعباً كل ليلة بالخاص\n"
            "🕵️ المحقق — يكشف دور لاعب كل ليلة بالخاص\n"
            "👤 المواطن — يحاول يكشف القاتل بالتصويت\n\n"
            "🔄 كيف تلعب:\n"
            "1️⃣ اكتب القاتل في المجموعة لفتح التسجيل\n"
            "2️⃣ اللاعبون يضغون زر 'انضم للعبة'\n"
            "3️⃣ من فتح اللعبة يكتب بدأ لبدء توزيع الأدوار\n"
            "4️⃣ 🌙 الليل: القاتل والمحقق يرسلون اختياراتهم للبوت بالخاص\n"
            "5️⃣ ☀️ النهار: البوت يعلن الضحية، الكل يصوت لطرد مشتبه\n"
            "6️⃣ يتكرر حتى يفوز فريق\n\n"
            "🏆 شروط الفوز:\n"
            "👥 المواطنون يفوزون إذا طردوا القاتل\n"
            "🔪 القاتل يفوز إذا بقي هو ولاعب واحد فقط\n\n"
            "⚠️ للإلغاء: إيقاف القاتل"
        )
    else:
        return

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🔙 رجوع", callback_data="guide_back"))
    safe_edit(call.message.chat.id, call.message.message_id, text, reply_markup=markup)


# ============================================================
# نظام الألعاب
# ============================================================

challenges = {}


@bot.message_handler(func=lambda m: m.text in ("ك", "ف", "ر", "ت", "نت", "م", "كمله", "ج"))
def start_game(message):
    cid = message.chat.id
    text = message.text
    raw_val = ""

    if text in ("ك", "ف", "كمله"):
        word = random.choice(words_list)
    elif text == "ج":
        if not sentences_list:
            return bot.reply_to(message, "⚠️ قائمة الجمل فارغة! اطلب من المطور إضافة جمل.")
        word = random.choice(sentences_list)
    elif text == "ر":
        length = random.randint(9, 10)
        raw_val = "".join([str(random.randint(0, 9)) for _ in range(length)])
        word = " ".join([raw_val[::-1][i:i+3] for i in range(0, len(raw_val), 3)])[::-1]
    elif text == "ت":
        length = 5
        raw_val = "".join([str(random.randint(0, 9)) for _ in range(length)])
        word = " ".join([raw_val[::-1][i:i+3] for i in range(0, len(raw_val), 3)])[::-1]
    elif text == "نت":
        word = str(random.randint(10, 99))
    elif text == "م":
        word = str(random.randint(100, 999))

    challenges[cid] = {"v": raw_val if text in ("ر", "ت") else word, "t": time.time(), "type": text}

    if text == "كمله":
        bot.reply_to(message, f"🔤 فكك الكلمة بوضع مسافة بين كل حرف:\n\n『 {word} 』")
    elif text == "ج":
        bot.reply_to(message, f"『 {word} 』")
    else:
        bot.reply_to(message, word)


# ============================================================
# أوامر المال والحساب
# ============================================================

@bot.message_handler(func=lambda m: m.text == "حسابي")
def my_account(message):
    uid = str(message.from_user.id)
    user = get_user_data(uid, message.from_user.first_name)
    gang_name, _ = get_user_gang(uid)

    if not user.get('acc_id'):
        return bot.reply_to(message, f"⚠️ ما عندك حساب بنكي، نقاطك: {user['total_pts']}")

    gang_line = f"⇜ العصابة ↢ {gang_name}\n" if gang_name else ""
    res = (
        f"⇜ الاسم ↢ {user['name']}\n"
        f"⇜ رقم الحساب ↢ {user['acc_id']}\n"
        f"⇜ البنك ↢ {user['bank_type']}\n"
        f"⇜ نوع البطاقة ↢ {user['card_type']}\n"
        f"⇜ الرصيد ↢ {format_num(user['pts'])} دينار 💸\n"
        f"⇜ النقاط ↢ {format_num(user['total_pts'])} نقطة 🏅\n"
        f"{gang_line}༄"
    )
    bot.reply_to(message, res)


@bot.message_handler(func=lambda m: m.text == "فلوسي")
def my_money(message):
    uid = str(message.from_user.id)
    user = get_user_data(uid)
    if not user.get('acc_id'):
        return bot.reply_to(message, "❌ ما عندك حساب بنكي.")
    bot.reply_to(message, f"⇜ رصيدك الحالي ↢ {format_num(user['pts'])} دينار 💸")


@bot.message_handler(func=lambda m: m.text == "بخشيش")
def tip_cmd(message):
    uid = str(message.from_user.id)
    user = get_user_data(uid, message.from_user.first_name)
    if not user.get('acc_id'): return
    now = time.time()
    if now - user.get('last_tip', 0) < 300:
        rem = int(300 - (now - user['last_tip']))
        return bot.reply_to(message, f"⏳ البخشيش الجاي بعد {rem // 60} دقيقة و {rem % 60} ثانية")
    amt = random.randint(500, 1500)
    with data_lock:
        user['pts'] += amt
        user['last_tip'] = now
        mark_dirty()
    bot.reply_to(message, f"🎁 حصلت بخشيش!\n⇜ المبلغ ↢ {format_num(amt)} دينار 💸")


@bot.message_handler(func=lambda m: m.text and m.text.startswith("حظ"))
def luck_cmd(message):
    uid = str(message.from_user.id)
    user = get_user_data(uid, message.from_user.first_name)
    if not user.get('acc_id'): return
    try:
        amount = int(message.text.split()[1])
        if amount > user['pts']: return bot.reply_to(message, "❌ رصيدك ما يكفي")
        if amount < 50: return bot.reply_to(message, "❌ اقل مبلغ 50 دينار")
        old_pts = user['pts']
        with data_lock:
            if random.choice([True, False]):
                user['pts'] += amount
                mark_dirty()
                bot.reply_to(message, f"⇜ مبروك فزت!\n⇜ قبل: {format_num(old_pts)}\n⇜ الان: {format_num(user['pts'])}")
            else:
                user['pts'] -= amount
                mark_dirty()
                bot.reply_to(message, f"⇜ خسرت!\n⇜ قبل: {format_num(old_pts)}\n⇜ الان: {format_num(user['pts'])}")
    except:
        bot.reply_to(message, "📋 الصيغة: حظ (المبلغ)")


@bot.message_handler(func=lambda m: m.text and m.text.startswith("مضاربه"))
def trade_cmd(message):
    uid = str(message.from_user.id)
    user = get_user_data(uid, message.from_user.first_name)
    if not user.get('acc_id'): return
    try:
        amount = int(message.text.split()[1])
        if amount > user['pts']: return bot.reply_to(message, "❌ رصيدك ما يكفي")
        p = random.randint(1, 100)
        with data_lock:
            if random.choice([True, False]):
                win = int(amount * (p / 100))
                user['pts'] += win
                mark_dirty()
                bot.reply_to(message, f"📈 ربح +{p}%\n⇜ الربح: {format_num(win)} دينار\n⇜ رصيدك: {format_num(user['pts'])}")
            else:
                lose = int(amount * (p / 100))
                user['pts'] -= lose
                mark_dirty()
                bot.reply_to(message, f"📉 خسارة -{p}%\n⇜ الخسارة: {format_num(lose)} دينار\n⇜ رصيدك: {format_num(user['pts'])}")
    except:
        bot.reply_to(message, "📋 الصيغة: مضاربه (المبلغ)")


@bot.message_handler(func=lambda m: m.text and m.text.startswith("استثمار"))
def invest_cmd(message):
    uid = str(message.from_user.id)
    user = get_user_data(uid)
    if not user.get('acc_id'): return
    try:
        amount = int(message.text.split()[1])
        now = time.time()
        if amount > user['pts']: return bot.reply_to(message, "❌ رصيدك ما يكفي")
        if now - user.get('last_invest', 0) < 900:
            rem = int(900 - (now - user['last_invest']))
            return bot.reply_to(message, f"⏳ الاستثمار القادم بعد {rem // 60} دقيقة")
        p = random.randint(1, 15)
        win = int(amount * (p / 100))
        with data_lock:
            user['pts'] += win
            user['last_invest'] = now
            mark_dirty()
        bot.reply_to(message, f"⇜ استثمار ناجح! ربح {p}%\n⇜ الربح: {format_num(win)} دينار\n⇜ رصيدك: {format_num(user['pts'])}")
    except:
        bot.reply_to(message, "📋 الصيغة: استثمار (المبلغ)")


@bot.message_handler(func=lambda m: m.text == "راتب")
def salary_cmd(message):
    uid = str(message.from_user.id)
    user = get_user_data(uid, message.from_user.first_name)
    if not user.get('acc_id'): return
    now = time.time()
    if now - user.get('last_salary', 0) < 900:
        rem = int(900 - (now - user['last_salary']))
        return bot.reply_to(message, f"⏳ الراتب القادم بعد {rem // 60} دقيقة")
    amt = 2200
    with data_lock:
        user['pts'] += amt
        user['last_salary'] = now
        mark_dirty()
    bot.reply_to(message, f"📩 تم ايداع الراتب: {format_num(amt)} دينار\n⇜ الوظيفة: مبرمج\n⇜ رصيدك: {format_num(user['pts'])} دينار")


@bot.message_handler(func=lambda m: m.text == "زرف")
def rob_cmd(message):
    uid = str(message.from_user.id)
    user = get_user_data(uid, message.from_user.first_name)
    if not user.get('acc_id') or not message.reply_to_message: return
    now = time.time()
    if now - user.get('last_rob', 0) < 600:
        return bot.reply_to(message, "⏳ انتظر قليلاً، الشرطة تراقب!")
    target_uid = str(message.reply_to_message.from_user.id)
    target = get_user_data(target_uid, message.reply_to_message.from_user.first_name)
    if not target.get('acc_id'): return bot.reply_to(message, "❌ الشخص ما عنده حساب بنكي")
    with data_lock:
        user['last_rob'] = now
        if random.choice([True, False]) and target['pts'] > 500:
            amt = int(target['pts'] * 0.1)
            user['pts'] += amt
            target['pts'] -= amt
            mark_dirty()
            bot.reply_to(message, f"⚔️ تمت عملية الزرف!\n⇜ زرفت من: {target['name']}\n⇜ المبلغ: {format_num(amt)} دينار")
        else:
            user['pts'] = max(0, user['pts'] - 1000)
            mark_dirty()
            bot.reply_to(message, "🚔 انقبض عليك! غرامة 1,000 دينار")


@bot.message_handler(func=lambda m: m.text and m.text.startswith("تحويل"))
def transfer_money(message):
    uid = str(message.from_user.id)
    user = get_user_data(uid, message.from_user.first_name)
    if not user.get('acc_id'): return bot.reply_to(message, "⚠️ ما عندك حساب بنكي")
    try:
        parts = message.text.split()
        amount = int(parts[1])
        target_acc_id = str(parts[3])
        if amount <= 0 or amount > user['pts']: return bot.reply_to(message, "❌ رصيدك ما يكفي")
        target_uid = acc_index.get(target_acc_id)
        if not target_uid or target_uid == uid: return bot.reply_to(message, "❌ الحساب غير صحيح!")
        with data_lock:
            user['pts'] -= amount
            user_points[target_uid]['pts'] += amount
            mark_dirty()
        bot.reply_to(message, f"✅ تم تحويل {format_num(amount)} دينار إلى حساب {target_acc_id}")
    except:
        bot.reply_to(message, "📋 الصيغة: تحويل (المبلغ) الى (رقم الحساب)")


# ============================================================
# 📊 احصائياتي — إحصائيات اللاعب مع صورة الملف الشخصي
# ============================================================

def get_stats_rank(data):
    bt = data.get("best_time", 999.0)
    total = data.get("total_pts", 0)
    if total == 0:
        return "🆕 مبتدئ"
    if bt <= 0.50:
        return "👑 ملك الاسرع"
    elif bt <= 1.00:
        return "🥇 أسطوري"
    elif bt <= 1.50:
        return "🥈 فضي"
    elif bt <= 2.50:
        return "🥉 برونزي"
    elif bt <= 4.00:
        return "🎖️ محترف"
    else:
        return "👤 لاعب"


def _game_stat_line(user, label, time_key, val_key=None):
    bt = user.get(time_key, 999.0)
    if bt >= 999.0:
        return f"   {label}: لم يلعب بعد\n"
    val = user.get(val_key, "") if val_key else ""
    val_part = f" [{val}]" if val else ""
    return f"   {label}: ⏱️ {bt}ث{val_part}\n"


@bot.message_handler(func=lambda m: m.text == "اح")
def my_stats(message):
    uid = str(message.from_user.id)
    user = get_user_data(uid, message.from_user.first_name)
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    rank = get_stats_rank(user)
    best = user.get("best_time", 999.0)
    best_str = f"{best} ثانية" if best < 999.0 else "لم يلعب بعد"
    gang_name, _ = get_user_gang(uid)
    gang_line = f"🛡️ العصابة: {gang_name}\n" if gang_name else ""

    caption = (
        f"📊 إحصائياتك\n\n"
        f"👤 {user['name']} | {username}\n"
        f"🏅 {rank}\n"
        f"{gang_line}\n"
        f"💰 الرصيد: {format_num(user.get('pts', 0))} دينار\n"
        f"🏆 مجموع الإجابات: {format_num(user.get('total_pts', 0))}\n"
        f"⚡ أفضل وقت كلي: {best_str}\n\n"
        f"📋 أفضل وقت لكل لعبة:\n"
        + _game_stat_line(user, "🔤 ك", "best_time_k", "best_val_k")
        + _game_stat_line(user, "🧩 ف", "best_time_f", "best_val_f")
        + _game_stat_line(user, "💯 ر", "best_time_r", "best_val_r")
        + _game_stat_line(user, "🌐 نت", "best_time_net", "best_val_net")
        + _game_stat_line(user, "🔢 م", "best_time_m", "best_val_m")
        + _game_stat_line(user, "📝 ج", "best_time_j", "best_val_j")
        + "༄"
    )

    try:
        photos = bot.get_user_profile_photos(message.from_user.id, limit=1)
        if photos.total_count > 0:
            file_id = photos.photos[0][0].file_id
            bot.send_photo(message.chat.id, file_id, caption=caption, reply_to_message_id=message.message_id)
        else:
            bot.reply_to(message, caption)
    except Exception:
        bot.reply_to(message, caption)


# ============================================================
# 🏆 توب الكروبات — أقوى المجموعات بالنقاط
# ============================================================

@bot.message_handler(func=lambda m: m.text == "توب الكروبات")
def top_groups(message):
    if not groups_data:
        return bot.reply_to(message, "⚠️ لا توجد بيانات كروبات حالياً!\nيجب أن تُلعب الألعاب في المجموعات أولاً.")

    sorted_groups = sorted(groups_data.items(), key=lambda x: x[1].get("total_pts", 0), reverse=True)[:10]
    icons = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    res = "🏆 توب الكروبات\n\n"
    for i, (gid, ginfo) in enumerate(sorted_groups):
        name = ginfo.get("name", "مجموعة مجهولة")
        pts = ginfo.get("total_pts", 0)
        res += f"{icons[i]} {name}\n"
        res += f"   🏅 {format_num(pts)} نقطة\n\n"

    bot.reply_to(message, res + "༄")


# ============================================================
# أوامر إدارة الجمل (مطورين) — قبل catch-all
# ============================================================

@bot.message_handler(commands=['أضف_جمله'], func=lambda m: m.from_user.id in developers)
def add_sentence(message):
    try:
        sentence = message.text.split(maxsplit=1)[1].strip()
    except:
        return bot.reply_to(message, "📋 الصيغة: /أضف_جمله (الجملة)\nمثال: /أضف_جمله الكتاب خير جليس")
    word_count = len(sentence.split())
    if word_count < 3 or word_count > 5:
        return bot.reply_to(message, "❌ الجملة يجب أن تكون من 3 إلى 5 كلمات!")
    if sentence in sentences_list:
        return bot.reply_to(message, "⚠️ الجملة موجودة أصلاً في القائمة!")
    sentences_list.append(sentence)
    mark_dirty()
    bot.reply_to(message, f"✅ تمت إضافة الجملة بنجاح!\n📝 [{sentence}]\n📚 المجموع: {len(sentences_list)} جملة")


@bot.message_handler(commands=['حذف_جمله'], func=lambda m: m.from_user.id in developers)
def delete_sentence(message):
    try:
        sentence = message.text.split(maxsplit=1)[1].strip()
    except:
        return bot.reply_to(message, "📋 الصيغة: /حذف_جمله (الجملة)\nمثال: /حذف_جمله الوقت من ذهب")
    if sentence not in sentences_list:
        return bot.reply_to(message, f"❌ الجملة [{sentence}] غير موجودة في القائمة!")
    sentences_list.remove(sentence)
    mark_dirty()
    bot.reply_to(message, f"✅ تم حذف الجملة [{sentence}].\n📚 المجموع: {len(sentences_list)} جملة")


@bot.message_handler(commands=['عرض_الجمل'], func=lambda m: m.from_user.id in developers)
def list_all_sentences(message):
    if not sentences_list:
        return bot.reply_to(message, "⚠️ قائمة الجمل فارغة!")
    chunk_size = 20
    chunks = [sentences_list[i:i+chunk_size] for i in range(0, len(sentences_list), chunk_size)]
    for idx, chunk in enumerate(chunks):
        text = f"📚 قائمة الجمل ({len(sentences_list)} جملة) — صفحة {idx+1}/{len(chunks)}:\n\n"
        for i, s in enumerate(chunk, idx*chunk_size+1):
            text += f"{i}. {s}\n"
        bot.reply_to(message, text)


# ============================================================
# 🔪 لعبة القاتل
# ============================================================

killer_games = {}
killer_night = {}


def killer_player_list(game):
    lines = []
    for i, (uid, p) in enumerate(game["players"].items(), 1):
        status = "💀" if not p["alive"] else "👤"
        lines.append(f"{i}. {status} {p['name']}")
    return "\n".join(lines)


def killer_alive_list(game):
    return {uid: p for uid, p in game["players"].items() if p["alive"]}


def killer_check_win(cid):
    game = killer_games.get(cid)
    if not game:
        return False
    alive = killer_alive_list(game)
    killer = game["killer"]
    if killer not in alive:
        winners = [p["name"] for uid, p in alive.items()]
        bot.send_message(cid,
            f"🎉 فاز المواطنون!\n"
            f"🔪 القاتل كان: {game['players'][killer]['name']}\n"
            f"🏆 الأحياء: {', '.join(winners)}")
        killer_cleanup(cid)
        return True
    if len(alive) <= 2:
        bot.send_message(cid,
            f"🔪 فاز القاتل!\n"
            f"👑 القاتل: {game['players'][killer]['name']}")
        killer_cleanup(cid)
        return True
    return False


def killer_cleanup(cid):
    game = killer_games.pop(cid, None)
    if game:
        for uid in game["players"]:
            killer_night.pop(uid, None)


def killer_start_night(cid):
    game = killer_games.get(cid)
    if not game:
        return
    game["phase"] = "night"
    game["night_kill"] = None
    game["night_investigate"] = None
    alive = killer_alive_list(game)

    numbered = []
    for i, (uid, p) in enumerate(alive.items(), 1):
        numbered.append(f"{i}. {p['name']}")
    player_txt = "\n".join(numbered)

    bot.send_message(cid,
        f"🌙 الليل بدأ...\n\n"
        f"📩 القاتل والمحقق: أرسلوا رقم اختياركم للبوت بالخاص!\n\n"
        f"اللاعبون الأحياء:\n{player_txt}")

    killer = game["killer"]
    detective = game.get("detective")

    for uid in game["players"]:
        killer_night.pop(uid, None)

    try:
        bot.send_message(int(killer),
            f"🔪 دورك! اختر من تقتل:\n\n{player_txt}\n\nأرسل الرقم:")
        killer_night[killer] = cid
    except:
        pass

    if detective and detective in alive:
        try:
            bot.send_message(int(detective),
                f"🕵️ دورك! اختر من تحقق معه:\n\n{player_txt}\n\nأرسل الرقم:")
            killer_night[detective] = cid
        except:
            pass

    def night_timeout():
        time.sleep(60)
        g = killer_games.get(cid)
        if g and g.get("phase") == "night":
            killer_start_day(cid)
    threading.Thread(target=night_timeout, daemon=True).start()


def killer_start_day(cid):
    game = killer_games.get(cid)
    if not game or game.get("phase") != "night":
        return
    game["phase"] = "day"

    victim_uid = game.get("night_kill")
    if victim_uid and victim_uid in game["players"]:
        game["players"][victim_uid]["alive"] = False
        vname = game["players"][victim_uid]["name"]
        bot.send_message(cid, f"☀️ الصبح جاء...\n\n💀 {vname} قُتل الليلة!\n\nحان وقت التصويت!")
    else:
        bot.send_message(cid, f"☀️ الصبح جاء...\n\n😮 لم يُقتل أحد الليلة!\n\nحان وقت التصويت!")

    if killer_check_win(cid):
        return

    killer_start_vote(cid)


def killer_start_vote(cid):
    game = killer_games.get(cid)
    if not game:
        return
    game["phase"] = "vote"
    game["votes"] = {}
    alive = killer_alive_list(game)

    markup = InlineKeyboardMarkup()
    for uid, p in alive.items():
        markup.row(InlineKeyboardButton(f"🗳️ {p['name']}", callback_data=f"kvote_{cid}_{uid}"))

    bot.send_message(cid,
        "🗳️ وقت التصويت!\nمن تشك فيه؟ صوّت الآن (دقيقة واحدة):",
        reply_markup=markup)

    def vote_timeout():
        time.sleep(60)
        g = killer_games.get(cid)
        if g and g.get("phase") == "vote":
            killer_end_vote(cid)
    threading.Thread(target=vote_timeout, daemon=True).start()


def killer_end_vote(cid):
    game = killer_games.get(cid)
    if not game:
        return
    votes = game.get("votes", {})
    if not votes:
        bot.send_message(cid, "⚠️ ما أحد صوّت! الليل يبدأ من جديد.")
        killer_start_night(cid)
        return

    count = {}
    for v in votes.values():
        count[v] = count.get(v, 0) + 1

    eliminated = max(count, key=count.get)
    ename = game["players"][eliminated]["name"]
    erole = "🔪 القاتل" if eliminated == game["killer"] else \
            "🕵️ المحقق" if eliminated == game.get("detective") else "👤 مواطن"

    game["players"][eliminated]["alive"] = False
    killer_night.pop(eliminated, None)

    bot.send_message(cid,
        f"⚖️ تم طرد: {ename}\n"
        f"دوره كان: {erole}\n"
        f"الأصوات: {count[eliminated]}")

    if not killer_check_win(cid):
        game["round"] = game.get("round", 1) + 1
        killer_start_night(cid)


@bot.message_handler(func=lambda m: m.text == "القاتل" and m.chat.type != "private")
def start_killer_game(message):
    cid = message.chat.id
    if cid in killer_games:
        return bot.reply_to(message, "❌ يوجد لعبة قاتل تسير الآن! اكتب 'إيقاف القاتل' لإلغائها.")

    uid = str(message.from_user.id)
    killer_games[cid] = {
        "phase": "joining",
        "players": {},
        "host": uid,
        "killer": None,
        "detective": None,
        "votes": {},
        "round": 1
    }

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("✋ انضم للعبة", callback_data=f"kjoin_{cid}"))

    bot.send_message(cid,
        "🔪 لعبة القاتل بدأت التسجيل!\n\n"
        "اضغط الزر للانضمام 👇\n"
        "عندما يكتمل اللاعبون، من فتح اللعبة يكتب: بدأ",
        reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("kjoin_"))
def handle_killer_join(call):
    cid = int(call.data[6:])
    uid = str(call.from_user.id)
    game = killer_games.get(cid)

    if not game:
        return bot.answer_callback_query(call.id, "❌ اللعبة انتهت!", show_alert=True)
    if game["phase"] != "joining":
        return bot.answer_callback_query(call.id, "❌ التسجيل أُغلق!", show_alert=True)
    if uid in game["players"]:
        return bot.answer_callback_query(call.id, "✅ أنت مسجل بالفعل!", show_alert=True)

    game["players"][uid] = {"name": call.from_user.first_name, "alive": True, "role": None}
    count = len(game["players"])
    bot.answer_callback_query(call.id, f"✅ انضممت! إجمالي اللاعبين: {count}", show_alert=True)
    bot.send_message(cid, f"✋ {call.from_user.first_name} انضم! إجمالي: {count} لاعب")


@bot.message_handler(func=lambda m: m.text == "بدأ" and m.chat.type != "private")
def begin_killer_game(message):
    cid = message.chat.id
    uid = str(message.from_user.id)
    game = killer_games.get(cid)

    if not game or game["phase"] != "joining":
        return
    if game["host"] != uid:
        return bot.reply_to(message, "❌ فقط من فتح اللعبة يقدر يبدأها!")
    if len(game["players"]) < 2:
        return bot.reply_to(message, "❌ تحتاج لاعبين على الأقل!")

    # فحص من يمكن الوصول إليه بالخاص قبل بدء اللعبة
    kicked = []
    reachable = {}
    for uid_p, p in game["players"].items():
        try:
            bot.send_message(int(uid_p),
                "⏳ لعبة القاتل على وشك تبدأ!\n"
                "انتظر، راح يوصلك دورك بالخاص...")
            reachable[uid_p] = p
        except:
            kicked.append(p["name"])

    if kicked:
        bot.send_message(cid,
            f"⚠️ تم طرد {len(kicked)} لاعب تلقائياً لأنهم لم يبدأوا البوت بالخاص:\n"
            + "\n".join(f"• {n}" for n in kicked)
            + "\n\n💡 لتجنب هذا في المرة القادمة: أرسل /start للبوت بالخاص أولاً!")

    game["players"] = reachable

    if len(game["players"]) < 2:
        bot.send_message(cid, "❌ ما يكفي لاعبين بعد الطرد! تم إلغاء اللعبة.")
        killer_cleanup(cid)
        return

    players = list(game["players"].keys())
    random.shuffle(players)

    game["killer"] = players[0]
    game["detective"] = players[1] if len(players) >= 3 else None

    for uid_p, p in game["players"].items():
        if uid_p == game["killer"]:
            p["role"] = "killer"
        elif uid_p == game.get("detective"):
            p["role"] = "detective"
        else:
            p["role"] = "civilian"

    bot.send_message(cid,
        f"🎮 اللعبة بدأت! {len(players)} لاعبين\n"
        f"📩 كل لاعب راح يوصله دوره بالخاص!")

    for uid_p, p in game["players"].items():
        role_txt = {
            "killer": "🔪 أنت القاتل! اختر ضحاياك بالخاص كل ليلة.",
            "detective": "🕵️ أنت المحقق! تقدر تكشف دور لاعب كل ليلة.",
            "civilian": "👤 أنت مواطن! حاول تكشف القاتل بالتصويت."
        }[p["role"]]
        try:
            bot.send_message(int(uid_p), f"🔪 لعبة القاتل بدأت!\n\n{role_txt}")
        except:
            pass

    killer_start_night(cid)


@bot.message_handler(func=lambda m: m.chat.type == "private" and str(m.from_user.id) in killer_night)
def handle_killer_night_action(message):
    uid = str(message.from_user.id)
    cid = killer_night.get(uid)
    game = killer_games.get(cid)

    if not game or game.get("phase") != "night":
        return

    try:
        choice = int(message.text.strip()) - 1
    except:
        return bot.send_message(message.chat.id, "❌ أرسل رقم فقط!")

    alive = list(killer_alive_list(game).keys())
    if choice < 0 or choice >= len(alive):
        return bot.send_message(message.chat.id, f"❌ رقم غير صحيح! اختر بين 1 و {len(alive)}")

    target_uid = alive[choice]
    target_name = game["players"][target_uid]["name"]

    if uid == game["killer"]:
        if target_uid == uid:
            return bot.send_message(message.chat.id, "❌ ما تقدر تقتل نفسك!")
        game["night_kill"] = target_uid
        killer_night.pop(uid, None)
        bot.send_message(message.chat.id, f"✅ اخترت قتل: {target_name}\nانتظر الصباح...")

    elif uid == game.get("detective"):
        role = game["players"][target_uid]["role"]
        role_txt = "🔪 قاتل!" if role == "killer" else "✅ بريء (مش قاتل)"
        killer_night.pop(uid, None)
        bot.send_message(message.chat.id, f"🕵️ {target_name} هو: {role_txt}")

    # ابدأ النهار إذا القاتل تصرف والمحقق تصرف (أو ميت/غير موجود)
    detective = game.get("detective")
    killer_acted = game.get("night_kill") is not None
    detective_absent = (detective is None
                        or detective not in killer_alive_list(game)
                        or detective not in killer_night)
    if killer_acted and detective_absent:
        killer_start_day(cid)


@bot.callback_query_handler(func=lambda call: call.data.startswith("kvote_"))
def handle_killer_vote(call):
    parts = call.data.split("_")
    cid = int(parts[1])
    target_uid = parts[2]
    uid = str(call.from_user.id)
    game = killer_games.get(cid)

    if not game or game.get("phase") != "vote":
        return bot.answer_callback_query(call.id, "❌ التصويت انتهى!", show_alert=True)
    if uid not in killer_alive_list(game):
        return bot.answer_callback_query(call.id, "❌ الأموات ما يصوتون!", show_alert=True)
    if uid == target_uid:
        return bot.answer_callback_query(call.id, "❌ ما تقدر تصوت على نفسك!", show_alert=True)

    game["votes"][uid] = target_uid
    tname = game["players"][target_uid]["name"]
    bot.answer_callback_query(call.id, f"✅ صوتك لـ {tname}", show_alert=True)

    alive_count = len(killer_alive_list(game))
    if len(game["votes"]) >= alive_count:
        killer_end_vote(cid)


@bot.message_handler(func=lambda m: m.text == "إيقاف القاتل" and m.chat.type != "private")
def stop_killer_game(message):
    cid = message.chat.id
    uid = str(message.from_user.id)
    game = killer_games.get(cid)

    if not game:
        return bot.reply_to(message, "❌ ما في لعبة قاتل الآن!")
    if game["host"] != uid and uid not in [str(d) for d in developers]:
        return bot.reply_to(message, "❌ فقط من فتح اللعبة يقدر يوقفها!")

    killer_cleanup(cid)
    bot.reply_to(message, "⛔ تم إيقاف لعبة القاتل.")


# ============================================================
# التحقق من الإجابات (يشمل حروب العصابات)
# ============================================================

@bot.message_handler(func=lambda m: not (m.text and m.text.startswith("/")))
def check_all_answers(message):
    cid = message.chat.id
    uid = str(message.from_user.id)

    if cid in gang_wars:
        war = gang_wars[cid]
        idx = war["round_idx"]

        if idx < 0 or war.get("round_winner") is not None:
            return

        gang_name = uid_to_gang.get(uid)
        if gang_name not in (war["gang1"], war["gang2"]):
            return

        if uid in war["answered_this_round"]:
            return

        war["answered_this_round"].add(uid)
        current = war["rounds"][idx]
        answer = message.text.strip()

        if current["type"] == "word":
            correct = normalize_text(answer) == normalize_text(current["value"])
        else:
            correct = "".join(filter(str.isdigit, answer)) == current["value"]

        if correct:
            dt = round(time.time() - war["round_start"], 2)
            war["round_winner"] = uid
            war["scores"][gang_name] = war["scores"].get(gang_name, 0) + 1

            g1, g2 = war["gang1"], war["gang2"]
            s1 = war["scores"].get(g1, 0)
            s2 = war["scores"].get(g2, 0)

            bot.reply_to(
                message,
                f"✅ صحيح! [{gang_name}] تأخذ النقطة ⏱️ {dt}ث\n\n"
                f"📊 النتيجة الحالية:\n"
                f"🛡️ [{g1}]: {s1} | ⚔️ [{g2}]: {s2}"
            )

            def go_next():
                time.sleep(2)
                next_round(cid)
            threading.Thread(target=go_next, daemon=True).start()

        return

    if cid not in challenges:
        return

    game_data = challenges[cid]
    original = game_data["v"]
    g_type = game_data["type"]
    is_correct = False

    if g_type == "كمله":
        cleaned = message.text.replace(" ", "")
        if " " in message.text.strip() and normalize_text(cleaned) == normalize_text(original):
            is_correct = True
    elif g_type == "ف":
        tokens = message.text.strip().split()
        if tokens and all(len(t) == 1 for t in tokens) and normalize_text("".join(tokens)) == normalize_text(original):
            is_correct = True
    else:
        if normalize_text(message.text, g_type) == normalize_text(original, g_type):
            is_correct = True

    if is_correct:
        dt = round(time.time() - game_data["t"], 2)
        user = get_user_data(uid, message.from_user.first_name)

        with data_lock:
            user['total_pts'] += 1
            if dt < user.get('best_time', 999.0):
                user['best_time'] = dt

            map_types = {"نت": "net", "ر": "r", "ك": "k", "م": "m", "ف": "f", "ج": "j"}
            if g_type in map_types:
                suffix = map_types[g_type]
                time_key = f"best_time_{suffix}"
                val_key = f"best_val_{suffix}"
                if dt < user.get(time_key, 999.0):
                    user[time_key] = dt
                    user[val_key] = original

            user['pts'] = user.get('pts', 0) + 50
            mark_dirty()

        del challenges[cid]

        # تحديث نقاط المجموعة
        if message.chat.type in ("group", "supergroup"):
            gid = str(cid)
            if gid not in groups_data:
                groups_data[gid] = {"name": message.chat.title or "مجموعة", "total_pts": 0}
            groups_data[gid]["name"] = message.chat.title or groups_data[gid]["name"]
            groups_data[gid]["total_pts"] = groups_data[gid].get("total_pts", 0) + 1
            mark_dirty()

        rank = get_rank_title(dt)
        bot.reply_to(
            message,
            f"✅ صحيح! ⏱️ {dt} ثانية\n"
            f"⇜ الرتبة: {rank}\n"
            f"⇜ النقاط: {format_num(user['total_pts'])} 🏅\n"
            f"⇜ الرصيد: {format_num(user['pts'])} دينار 💸"
        )


# ============================================================
# ✅ التحقق من الاشتراك
# ============================================================

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def handle_check_sub(call):
    uid = call.from_user.id
    if is_subscribed(uid):
        bot.answer_callback_query(call.id, "✅ تم التحقق! يمكنك الآن استخدام البوت.", show_alert=True)
        safe_edit(call.message.chat.id, call.message.message_id, "✅ تم التحقق من اشتراكك!\nيمكنك الآن استخدام البوت 🎉")
    else:
        bot.answer_callback_query(call.id, "❌ لم تشترك بعد! اشترك أولاً ثم اضغط التحقق.", show_alert=True)


# ============================================================
# 🎲 لعبة الرقم المخفي (1v1)
# ============================================================

hidden_games = {}
user_in_hidden = {}
pending_hidden = {}


@bot.message_handler(func=lambda m: m.text == "خ" and m.reply_to_message and m.chat.type != "private")
def start_hidden_challenge(message):
    challenger = str(message.from_user.id)
    target = str(message.reply_to_message.from_user.id)

    if target == challenger:
        return bot.reply_to(message, "❌ لا تقدر تتحدى نفسك!")
    if message.reply_to_message.from_user.is_bot:
        return bot.reply_to(message, "❌ لا تقدر تتحدى البوت!")
    if challenger in user_in_hidden:
        return bot.reply_to(message, "❌ أنت بالفعل في لعبة! أرسل 'الغ لعبتي' بالخاص للإلغاء.")
    if target in user_in_hidden:
        return bot.reply_to(message, "❌ هذا اللاعب في لعبة حالياً!")

    c_name = message.from_user.first_name
    t_name = message.reply_to_message.from_user.first_name
    game_id = f"{challenger}_{target}_{int(time.time())}"

    pending_hidden[target] = {
        "challenger": challenger,
        "c_name": c_name,
        "t_name": t_name,
        "chat_id": message.chat.id,
        "game_id": game_id
    }

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ قبول", callback_data=f"hg_a_{target}"),
        InlineKeyboardButton("❌ رفض", callback_data=f"hg_r_{target}")
    )
    bot.reply_to(
        message,
        f"🎲 [{c_name}] يتحداك يا [{t_name}]!\n\n"
        f"🔢 لعبة الرقم المخفي (1 - 200)\n"
        f"📩 التخمينات تُرسل بالخاص للبوت\n"
        f"⏳ عندك دقيقة للرد!",
        reply_markup=markup
    )

    def expire():
        time.sleep(60)
        if pending_hidden.get(target, {}).get("game_id") == game_id:
            pending_hidden.pop(target, None)
    threading.Thread(target=expire, daemon=True).start()


@bot.callback_query_handler(func=lambda call: call.data.startswith("hg_a_") or call.data.startswith("hg_r_"))
def handle_hidden_response(call):
    uid = str(call.from_user.id)

    if call.data.startswith("hg_r_"):
        target_id = call.data[5:]
        if uid != target_id:
            return bot.answer_callback_query(call.id, "❌ هذا التحدي مش لك!", show_alert=True)
        pending_hidden.pop(target_id, None)
        return safe_edit(call.message.chat.id, call.message.message_id,
                         f"❌ [{call.from_user.first_name}] رفض التحدي.")

    target_id = call.data[5:]
    if uid != target_id:
        return bot.answer_callback_query(call.id, "❌ هذا التحدي مش لك!", show_alert=True)

    challenge = pending_hidden.pop(target_id, None)
    if not challenge:
        return bot.answer_callback_query(call.id, "❌ انتهت صلاحية التحدي!", show_alert=True)

    challenger = challenge["challenger"]
    if challenger in user_in_hidden or target_id in user_in_hidden:
        return bot.answer_callback_query(call.id, "❌ أحد اللاعبين في لعبة أخرى!", show_alert=True)

    game_id = challenge["game_id"]
    secret = random.randint(1, 200)

    hidden_games[game_id] = {
        "number": secret,
        "p1": challenger, "p1_name": challenge["c_name"],
        "p2": target_id,  "p2_name": challenge["t_name"],
        "turn": challenger,
        "chat_id": challenge["chat_id"],
        "tries": {challenger: 0, target_id: 0}
    }
    user_in_hidden[challenger] = game_id
    user_in_hidden[target_id] = game_id

    safe_edit(
        call.message.chat.id, call.message.message_id,
        f"✅ بدأت لعبة الرقم المخفي!\n\n"
        f"👤 {challenge['c_name']}  VS  {challenge['t_name']}\n"
        f"🔢 الرقم بين 1 - 200\n\n"
        f"📩 أرسل تخمينك للبوت بالخاص!\n"
        f"🎯 يبدأ: {challenge['c_name']}"
    )

    try:
        bot.send_message(int(challenger), f"🎲 دورك! أرسل رقم بين 1 و 200:")
    except:
        pass
    try:
        bot.send_message(int(target_id), f"⏳ انتظر دورك في لعبة الرقم المخفي...")
    except:
        pass


@bot.message_handler(func=lambda m: m.chat.type == "private" and str(m.from_user.id) in user_in_hidden)
def handle_hidden_guess(message):
    uid = str(message.from_user.id)
    game_id = user_in_hidden.get(uid)
    game = hidden_games.get(game_id)
    if not game:
        return

    if game["turn"] != uid:
        return bot.send_message(message.chat.id, "⏳ مو دورك! انتظر.")

    try:
        guess = int(message.text.strip())
    except:
        return bot.send_message(message.chat.id, "❌ أرسل رقم فقط!")

    if guess < 1 or guess > 200:
        return bot.send_message(message.chat.id, "❌ الرقم يجب بين 1 و 200!")

    game["tries"][uid] += 1
    secret = game["number"]
    other = game["p2"] if uid == game["p1"] else game["p1"]
    my_name = game["p1_name"] if uid == game["p1"] else game["p2_name"]
    other_name = game["p2_name"] if uid == game["p1"] else game["p1_name"]

    if guess == secret:
        tries = game["tries"][uid]
        bot.send_message(message.chat.id,
                         f"🎉 صح! الرقم كان {secret}\n🏆 فزت بـ {tries} محاولة!")
        try:
            bot.send_message(int(other),
                             f"😔 [{my_name}] خمّن الرقم!\nكان {secret}\nخسرت هذه الجولة.")
        except:
            pass
        bot.send_message(
            game["chat_id"],
            f"🏆 [{my_name}] فاز في لعبة الرقم المخفي!\n"
            f"🔢 الرقم كان: {secret}\n"
            f"🎯 عدد محاولاته: {tries}\n"
            f"💸 +100 دينار"
        )
        user = get_user_data(uid, message.from_user.first_name)
        with data_lock:
            user['pts'] = user.get('pts', 0) + 100
            user['total_pts'] = user.get('total_pts', 0) + 1
            mark_dirty()
        user_in_hidden.pop(game["p1"], None)
        user_in_hidden.pop(game["p2"], None)
        hidden_games.pop(game_id, None)

    elif guess < secret:
        bot.send_message(message.chat.id, f"📈 الرقم أكبر من {guess}!")
        game["turn"] = other
        try:
            bot.send_message(int(other), f"🎯 دورك! أرسل رقم بين 1 و 200:\n(تلميح: الرقم أكبر من {guess})")
        except:
            pass
        bot.send_message(game["chat_id"], f"🔄 دور [{other_name}] الآن!")
    else:
        bot.send_message(message.chat.id, f"📉 الرقم أصغر من {guess}!")
        game["turn"] = other
        try:
            bot.send_message(int(other), f"🎯 دورك! أرسل رقم بين 1 و 200:\n(تلميح: الرقم أصغر من {guess})")
        except:
            pass
        bot.send_message(game["chat_id"], f"🔄 دور [{other_name}] الآن!")


@bot.message_handler(func=lambda m: m.text == "الغ لعبتي" and m.chat.type == "private")
def cancel_hidden_game(message):
    uid = str(message.from_user.id)
    game_id = user_in_hidden.get(uid)
    if not game_id:
        return bot.send_message(message.chat.id, "❌ أنت لست في لعبة حالياً!")
    game = hidden_games.get(game_id)
    if game:
        other = game["p2"] if uid == game["p1"] else game["p1"]
        try:
            bot.send_message(int(other), "⚠️ الطرف الآخر ألغى اللعبة.")
        except:
            pass
        bot.send_message(game["chat_id"], "⚠️ تم إلغاء لعبة الرقم المخفي.")
        user_in_hidden.pop(game["p1"], None)
        user_in_hidden.pop(game["p2"], None)
        hidden_games.pop(game_id, None)
    bot.send_message(message.chat.id, "✅ تم إلغاء اللعبة.")


# ============================================================
# 🚫 أوامر الحظر — للمطورين
# ============================================================

@bot.message_handler(commands=['حضر_توب'], func=lambda m: m.from_user.id in developers)
def ban_from_tops(message):
    try:
        target_id = str(message.text.split()[1])
    except:
        return bot.reply_to(message, "📋 الصيغة: /حضر_توب (ID اللاعب)")
    if target_id in banned_tops:
        return bot.reply_to(message, f"⚠️ اللاعب [{target_id}] محظور من التوبات بالفعل!")
    banned_tops.add(target_id)
    mark_dirty()
    name = user_points.get(target_id, {}).get("name", target_id)
    bot.reply_to(message, f"🚫 تم حظر [{name}] من جميع التوبات.\n⇜ لا يزال يقدر يستخدم البوت.")


@bot.message_handler(commands=['رفع_توب'], func=lambda m: m.from_user.id in developers)
def unban_from_tops(message):
    try:
        target_id = str(message.text.split()[1])
    except:
        return bot.reply_to(message, "📋 الصيغة: /رفع_توب (ID اللاعب)")
    if target_id not in banned_tops:
        return bot.reply_to(message, f"⚠️ اللاعب [{target_id}] غير محظور من التوبات!")
    banned_tops.discard(target_id)
    mark_dirty()
    name = user_points.get(target_id, {}).get("name", target_id)
    bot.reply_to(message, f"✅ تم رفع حظر التوبات عن [{name}].")


@bot.message_handler(commands=['حضر_كلي'], func=lambda m: m.from_user.id in developers)
def ban_from_bot(message):
    try:
        target_id = str(message.text.split()[1])
    except:
        return bot.reply_to(message, "📋 الصيغة: /حضر_كلي (ID اللاعب)")
    if int(target_id) in developers:
        return bot.reply_to(message, "❌ لا يمكنك حظر مطور!")
    if target_id in banned_users:
        return bot.reply_to(message, f"⚠️ اللاعب [{target_id}] محظور نهائياً بالفعل!")
    banned_users.add(target_id)
    mark_dirty()
    name = user_points.get(target_id, {}).get("name", target_id)
    bot.reply_to(message, f"🔴 تم الحظر النهائي للاعب [{name}].\n⇜ لن يستطيع استخدام البوت نهائياً.")


@bot.message_handler(commands=['رفع_كلي'], func=lambda m: m.from_user.id in developers)
def unban_from_bot(message):
    try:
        target_id = str(message.text.split()[1])
    except:
        return bot.reply_to(message, "📋 الصيغة: /رفع_كلي (ID اللاعب)")
    if target_id not in banned_users:
        return bot.reply_to(message, f"⚠️ اللاعب [{target_id}] غير محظور نهائياً!")
    banned_users.discard(target_id)
    mark_dirty()
    name = user_points.get(target_id, {}).get("name", target_id)
    bot.reply_to(message, f"✅ تم رفع الحظر النهائي عن [{name}].")


# ============================================================
# 💡 نظام اقتراح الجمل من اللاعبين
# ============================================================

@bot.message_handler(func=lambda m: m.text and m.text.startswith("اقترح جمله"))
def suggest_sentence(message):
    uid = str(message.from_user.id)
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        return bot.reply_to(message, "📋 الصيغة: اقترح جمله (الجملة)\nمثال: اقترح جمله الكتاب خير جليس")

    sentence = parts[2].strip()
    word_count = len(sentence.split())
    if word_count < 3 or word_count > 5:
        return bot.reply_to(message, "❌ الجملة يجب أن تكون من 3 إلى 5 كلمات!")
    if sentence in sentences_list:
        return bot.reply_to(message, "⚠️ هذه الجملة موجودة بالفعل في البوت!")

    name = message.from_user.first_name
    username = f"@{message.from_user.username}" if message.from_user.username else name
    chat_name = message.chat.title if message.chat.type != "private" else "خاص"

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ قبول", callback_data=f"sug_acc_{uid}_{sentence[:40]}"),
        InlineKeyboardButton("❌ رفض",  callback_data=f"sug_rej_{uid}_{sentence[:40]}")
    )

    try:
        bot.send_message(
            MAIN_DEV,
            f"💡 اقتراح جملة جديدة!\n\n"
            f"📝 الجملة: [{sentence}]\n"
            f"👤 من: {name} ({username})\n"
            f"🆔 ID: {uid}\n"
            f"💬 المجموعة: {chat_name}\n\n"
            f"هل تريد إضافتها للعبة ج؟",
            reply_markup=markup
        )
        bot.reply_to(message, "✅ تم إرسال اقتراحك للمطور! انتظر الموافقة.")
    except Exception:
        bot.reply_to(message, "⚠️ تعذر إرسال الاقتراح، حاول لاحقاً.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("sug_acc_") or call.data.startswith("sug_rej_"))
def handle_sentence_suggestion(call):
    if call.from_user.id != MAIN_DEV:
        return bot.answer_callback_query(call.id, "❌ هذا القرار للمطور الرئيسي فقط!", show_alert=True)

    parts = call.data.split("_", 3)
    action  = parts[1]
    uid     = parts[2]
    sentence = parts[3]

    if action == "acc":
        if sentence not in sentences_list:
            sentences_list.append(sentence)
            mark_dirty()
        name = user_points.get(uid, {}).get("name", uid)
        safe_edit(
            call.message.chat.id, call.message.message_id,
            f"✅ تمت الموافقة على الجملة!\n📝 [{sentence}]\n📚 المجموع: {len(sentences_list)} جملة"
        )
        try:
            bot.send_message(int(uid),
                f"🎉 تمت الموافقة على جملتك المقترحة!\n"
                f"📝 [{sentence}]\n"
                f"تم إضافتها للعبة ج ✅"
            )
        except Exception:
            pass
    else:
        safe_edit(
            call.message.chat.id, call.message.message_id,
            f"❌ تم رفض الجملة: [{sentence}]"
        )
        try:
            bot.send_message(int(uid),
                f"😔 للأسف لم تتم الموافقة على جملتك المقترحة.\n"
                f"📝 [{sentence}]\nيمكنك اقتراح جملة أخرى!"
            )
        except Exception:
            pass


# ============================================================
# 👑 إدارة المطورين — فقط المطور الأصلي
# ============================================================

@bot.message_handler(commands=['اضف_مطور'], func=lambda m: m.from_user.id == MAIN_DEV)
def add_developer(message):
    try:
        new_dev_id = int(message.text.split()[1])
    except:
        return bot.reply_to(message, "📋 الصيغة: /اضف_مطور (ID المستخدم)")

    if new_dev_id in developers:
        return bot.reply_to(message, f"⚠️ المستخدم [{new_dev_id}] مطور بالفعل!")

    with data_lock:
        developers.append(new_dev_id)
        save_json(developers_file, developers)

    try:
        bot.send_message(new_dev_id,
            "🎉 تهانينا! تم تعيينك مطوراً في البوت.\n"
            "يمكنك الآن استخدام أوامر المطورين."
        )
    except:
        pass

    bot.reply_to(message, f"✅ تم إضافة [{new_dev_id}] كمطور بنجاح!\n📋 إجمالي المطورين: {len(developers)}")


@bot.message_handler(commands=['انزل_مطور'], func=lambda m: m.from_user.id == MAIN_DEV)
def remove_developer(message):
    try:
        dev_id = int(message.text.split()[1])
    except:
        return bot.reply_to(message, "📋 الصيغة: /انزل_مطور (ID المستخدم)")

    if dev_id == MAIN_DEV:
        return bot.reply_to(message, "❌ لا يمكنك إزالة المطور الأصلي!")

    if dev_id not in developers:
        return bot.reply_to(message, f"❌ المستخدم [{dev_id}] ليس مطوراً!")

    with data_lock:
        developers.remove(dev_id)
        save_json(developers_file, developers)

    try:
        bot.send_message(dev_id, "⚠️ تم إزالة صلاحياتك كمطور في البوت.")
    except:
        pass

    bot.reply_to(message, f"✅ تم إزالة [{dev_id}] من قائمة المطورين.\n📋 إجمالي المطورين: {len(developers)}")


@bot.message_handler(commands=['المطورين'], func=lambda m: m.from_user.id == MAIN_DEV)
def list_developers(message):
    if not developers:
        return bot.reply_to(message, "⚠️ لا يوجد مطورين!")

    res = f"👑 قائمة المطورين ({len(developers)}):\n\n"
    for i, dev_id in enumerate(developers, 1):
        tag = " ⭐ (أصلي)" if dev_id == MAIN_DEV else ""
        res += f"{i}. `{dev_id}`{tag}\n"

    res += "\n📋 لإضافة مطور: /اضف_مطور (ID)\n📋 لإزالة مطور: /انزل_مطور (ID)"
    bot.reply_to(message, res, parse_mode="Markdown")




# ============================================================
# تشغيل البوت
# ============================================================

if __name__ == "__main__":
    print("✅ البوت يعمل...")
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=60)
        except Exception as e:
            print(f"❌ خطأ: {e}")
            time.sleep(5)
