import logging
import sqlite3
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = '8176079820:AAGtsRhHmOg8t4J9AKjo0FV9Gj-obEK5wkI'
CHANNELS = ['@rtkhu']
ADMIN_ID = 6337688385
API_URL = 'https://rajanlinks.gt.tc/osint.php?key=test&phone={}'
BUY_CREDIT_TEXT = '''💳 Buy Credit Plans:
- 10 Credits: ₹20
- 20 Credits: ₹30
- 50 Credits: ₹70
- 100 Credits: ₹150
- 200 Credits: ₹200
- 500 Credits: ₹350
- Unlimited Credits: ₹999

DM to buy: @Ritik044'''

conn = sqlite3.connect('bot.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    credit INTEGER DEFAULT 20,
    referred_by INTEGER,
    redeemed_codes TEXT DEFAULT ''
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS redeem_codes (
    code TEXT PRIMARY KEY,
    credits INTEGER
)''')
conn.commit()

def get_user(user_id):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    return cursor.fetchone()

def update_credit(user_id, amount):
    cursor.execute('UPDATE users SET credit = credit + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()

def add_user(user_id, username, referred_by=None):
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username, credit, referred_by) VALUES (?, ?, 20, ?)',
                   (user_id, username, referred_by))
    conn.commit()

async def check_membership(bot, user_id, channel):
    try:
        member = await bot.get_chat_member(channel, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def format_search_result(data):
    if not data.get('success') or not data.get('data', {}).get('data'):
        return "❌ No information found."
    entries = data['data']['data']
    result = "📱 Phone Number Info:\n"
    for i, entry in enumerate(entries, 1):
        result += f"\n{i}. 📞 Mobile: {entry.get('mobile', 'N/A')}\n"
        result += f"   👤 Name: {entry.get('name', 'N/A')}\n"
        result += f"   👨‍👩‍👧‍👦 Father's Name: {entry.get('fname', 'N/A')}\n"
        result += f"   🏠 Address: {entry.get('address', 'N/A')}\n"
        result += f"   📱 Alternate: {entry.get('alt', 'N/A')}\n"
        result += f"   🌐 Circle: {entry.get('circle', 'N/A')}\n"
        result += f"   🆔 ID: {entry.get('id', 'N/A')}\n"
    return result

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    referred_by = None
    if context.args and context.args[0].isdigit():
        referred_by = int(context.args[0])
    add_user(user.id, user.username, referred_by)
    if referred_by:
        referrer = get_user(referred_by)
        if referrer:
            update_credit(referred_by, 2)
            await context.bot.send_message(referred_by, "🎉 आपने 2 credits कमाए हैं एक नए user को refer करने पर!")

    keyboard = [[InlineKeyboardButton(f"Join {ch}", url=f"https://t.me/{ch[1:]}")] for ch in CHANNELS]
    keyboard.append([InlineKeyboardButton("✅ Joined/Verify", callback_data='verify_join')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("स्वागत है! जारी रखने के लिए channel में join करें:", reply_markup=reply_markup)

async def verify_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    joined_all = all([await check_membership(context.bot, user_id, ch) for ch in CHANNELS])
    if joined_all:
        await query.edit_message_text("✅ Verification successful! यहाँ main menu है:")
        await show_main_menu(query.message, context)
    else:
        await query.edit_message_text("❌ पहले channel में join करें।")

async def show_main_menu(message, context):
    keyboard = [
        [KeyboardButton("🔍 Search Number")],
        [KeyboardButton("👤 My Profile")],
        [KeyboardButton("🔗 Refer and Get Credit")],
        [KeyboardButton("📞 Contact Admin")],
        [KeyboardButton("🎁 Redeem Code")],
        [KeyboardButton("💳 Buy Credit")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await message.reply_text("Main Menu:", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    user_data = get_user(user.id)
    if not user_data:
        await update.message.reply_text("कृपया /start से bot शुरू करें।")
        return

    if text == "🔍 Search Number":
        context.user_data['awaiting_number'] = True
        await update.message.reply_text("कृपया 10 अंकों का मोबाइल नंबर भेजें।")
    elif text == "👤 My Profile":
        credit = user_data[2]
        username = user_data[1] or "N/A"
        user_id = user_data[0]
        await update.message.reply_text(f"👤 Profile:\n- Username: {username}\n- User ID: {user_id}\n- Credits: {credit}")
    elif text == "🔗 Refer and Get Credit":
        refer_link = f"https://t.me/{context.bot.username}?start={user.id}"
        await update.message.reply_text(f"🔗 Referral link: {refer_link}\nहर referral पर 2 credits कमाएँ!")
    elif text == "📞 Contact Admin":
        context.user_data['contacting_admin'] = True
        await update.message.reply_text("कृपया अपना संदेश लिखें, मैं admin को भेज दूँगा।")
    elif text == "🎁 Redeem Code":
        context.user_data['awaiting_code'] = True
        await update.message.reply_text("कृपया अपना redeem code दर्ज करें।")
    elif text == "💳 Buy Credit":
        await update.message.reply_text(BUY_CREDIT_TEXT)
    elif context.user_data.get('awaiting_number'):
        if not text.isdigit() or len(text) != 10:
            await update.message.reply_text("❌ गलत नंबर। कृपया valid 10-digit number दर्ज करें।")
            return
        if user_data[2] <= 0:
            await update.message.reply_text("❌ आपके पास पर्याप्त credits नहीं हैं।")
            return
        try:
            response = requests.get(API_URL.format(text))
            try:
                data = response.json()
            except ValueError:
                await update.message.reply_text("❌ Invalid response from server.")
                return
            result = format_search_result(data)
            update_credit(user.id, -1)
            await update.message.reply_text(result)
        except:
            await update.message.reply_text("❌ Error: कृपया बाद में प्रयास करें।")
        context.user_data['awaiting_number'] = False
    elif context.user_data.get('awaiting_code'):
        cursor.execute('SELECT credits FROM redeem_codes WHERE code = ?', (text,))
        code_data = cursor.fetchone()
        if code_data:
            credits = code_data[0]
            redeemed = user_data[4].split(',') if user_data[4] else []
            if text in redeemed:
                await update.message.reply_text("❌ यह code पहले ही redeem हो चुका है।")
            else:
                update_credit(user.id, credits)
                redeemed.append(text)
                cursor.execute('UPDATE users SET redeemed_codes = ? WHERE user_id = ?', (','.join(redeemed), user.id))
                conn.commit()
                await update.message.reply_text(f"✅ {credits} credits जोड़े गए!")
        else:
            await update.message.reply_text("❌ गलत code।")
        context.user_data['awaiting_code'] = False
    elif context.user_data.get('contacting_admin'):
        await context.bot.send_message(ADMIN_ID, f"{user.username} ({user.id}) से message: {text}")
        await update.message.reply_text("✅ आपका संदेश admin को भेज दिया गया है।")
        context.user_data['contacting_admin'] = False

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(verify_join, pattern='verify_join'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == '__main__':
    main()
