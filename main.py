import logging
import sqlite3
import os
import time
import urllib.parse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ==========================================
# ⚙️ STATIC CONFIGURATION
# ==========================================
STATIC_TOKEN = "8713940970:AAHgA87t0OuwmN3J2e3au4f5wWv-CBrBVKY"
STATIC_ADMIN_ID = 8748495527
INTENT_API_BASE = "https://flipkart-offer-sell-live.wuaze.com/index.py?price={am"
DEFAULT_IMG = "https://i.ibb.co/Fk431qrP/IMG-20260329-153839-635.jpg"

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- DATABASE MANAGEMENT ---
def init_db():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
    cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price INTEGER, img_url TEXT, description TEXT)')
    conn.commit()
    
    cursor.execute('SELECT COUNT(*) FROM settings')
    if cursor.fetchone()[0] == 0:
        defaults = [
            ('paid_link', 'https://t.me/+hA_REfe14FViYmZl'),
            ('demo_link', 'https://t.me/+pOkKdQXndR05NWFl'),
            ('backup_demo_link', 'https://t.me/+pOkKdQXndR05NWFl'),
            ('upi_pa', 'bharatpe.8q0r1o2o4w98197@fbpe'), 
            ('upi_pn', 'Sarvesh Kumar'),
            ('start_image', DEFAULT_IMG),
            ('start_text', '🥵 <b>𝐀𝐋𝐋 𝐓𝐘𝐏𝐄 𝐕𝐈𝐃𝐄𝐎𝐒 𝐀𝐕𝐀𝐈𝐋𝐀𝐁𝐋𝐄 🍑💦</b>\n\n✅ 𝐅𝐮𝐥𝐥 𝐇𝐃 | ✅ 𝐈𝐧𝐬𝐭𝐚𝐧𝐭 𝐀𝐜𝐜𝐞𝐬𝐬'),
            ('premium_image', DEFAULT_IMG),
            ('premium_text', ''), 
            ('how_to_text', '📌 <b>𝐇𝐨𝐰 𝐭𝐨 𝐠𝐞𝐭 𝐏𝐫𝐞𝐦𝐢𝐮𝐦?</b>\n\n1. "💎 GET PREMIUM" dabayein.\n2. Category chunein.\n3. PAY NOW dabayein.\n4. Screenshot bhejein.\n5. Link milega! ⚡')
        ]
        cursor.executemany('INSERT INTO settings VALUES (?, ?)', defaults)
        
        cats = [
            ('🇮🇳 Indian Video', 25, DEFAULT_IMG, 'Indian models collection.'),
            ('❤️ Love Video', 30, DEFAULT_IMG, 'Romantic adult videos.'),
            ('💃 Masti Video', 35, DEFAULT_IMG, 'Webseries and short films.'),
            ('🇵🇰 Pakistan Video', 40, DEFAULT_IMG, 'Across border videos.')
        ]
        cursor.executemany('INSERT INTO categories (name, price, img_url, description) VALUES (?, ?, ?, ?)', cats)
        conn.commit()
    conn.close()

def read_setting(key):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else ""

def write_setting(key, value):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

def get_categories():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, price, img_url, description FROM categories')
    cats = cursor.fetchall()
    conn.close()
    return cats

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('bot_data.db')
    conn.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()
    
    reply_keyboard = [
        [KeyboardButton("💎 GET PREMIUM"), KeyboardButton("🎬 DEMO")],
        [KeyboardButton("❓ HOW TO GET PREMIUM")]
    ]
    reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

    inline_kb = [
        [InlineKeyboardButton("💎 GET PREMIUM", callback_data='menu_prem')],
        [InlineKeyboardButton("🎬 DEMO", callback_data='menu_demo')],
        [InlineKeyboardButton("❓ HOW TO GET PREMIUM", callback_data='menu_how')]
    ]
    
    start_img = read_setting('start_image') or DEFAULT_IMG
    start_text = read_setting('start_text') or "Welcome!"

    try:
        # 1. Niche wale buttons laane ke liye Telegram ke rule ke hisaab se ek text bhejna zaroori hai.
        # Isliye yahan sirf ek dot (.) lagaya hai taki koi bada kachra na dikhe.
        await update.message.reply_text(".", reply_markup=reply_markup)
        
        # 2. Phir aapki photo, text aur upar wale buttons ek sath.
        await update.message.reply_photo(
            photo=start_img, 
            caption=start_text, 
            reply_markup=InlineKeyboardMarkup(inline_kb),
            parse_mode='HTML'
        )
    except Exception as e:
        await update.message.reply_text("⚠️ Image error! Admin please update start photo via /set_start_img [URL]")

async def show_premium_flow(update_or_query, context):
    cats = get_categories()
    inline_cats = [[InlineKeyboardButton(f"{cat[1]} - ₹{cat[2]}", callback_data=f'cat_{cat[0]}')] for cat in cats]
    
    prem_image = read_setting('premium_image') or DEFAULT_IMG
    prem_text = read_setting('premium_text')
    
    if "Choose Video Category" in prem_text:
        prem_text = ""
        write_setting('premium_text', "")
        
    caption_to_send = prem_text if prem_text.strip() != "" else None
    
    target = update_or_query.message if hasattr(update_or_query, 'message') else update_or_query
    try:
        await target.reply_photo(
            photo=prem_image, 
            caption=caption_to_send, 
            reply_markup=InlineKeyboardMarkup(inline_cats), 
            parse_mode='HTML'
        )
    except Exception as e:
        await target.reply_text("⚠️ (Photo load error)", reply_markup=InlineKeyboardMarkup(inline_cats), parse_mode='HTML')

async def handle_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "💎 GET PREMIUM":
        await show_premium_flow(update, context)
    elif text == "🎬 DEMO":
        dl = read_setting('demo_link')
        t = f"🔥 <b>Demo Content:</b>\n👉 {dl}" if dl else "Currently demo not available."
        await update.message.reply_text(t, parse_mode='HTML')
    elif text == "❓ HOW TO GET PREMIUM":
        await update.message.reply_text(read_setting('how_to_text'), parse_mode='HTML')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # --- ADMIN APPROVE/DECLINE LOGIC ---
    if query.data.startswith('app_'):
        user_id = int(query.data.split('_')[1])
        paid_link = read_setting('paid_link')
        try:
            await context.bot.send_message(chat_id=user_id, text=f"✅ <b>Payment Verified!</b>\n\n🎉 Here is your Premium Link:\n👉 {paid_link}", parse_mode='HTML')
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ <b>APPROVED</b> by Admin", parse_mode='HTML')
        except Exception as e:
            await query.message.reply_text(f"❌ User blocked bot or error: {e}")
        return

    elif query.data.startswith('dec_'):
        user_id = int(query.data.split('_')[1])
        try:
            await context.bot.send_message(chat_id=user_id, text="❌ <b>Payment Declined!</b>\n\nFake or invalid screenshot. Contact Admin.", parse_mode='HTML')
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n❌ <b>DECLINED</b> by Admin", parse_mode='HTML')
        except Exception as e:
            pass
        return
    # -----------------------------------

    if query.data == 'menu_prem':
        await show_premium_flow(query, context)

    elif query.data == 'menu_demo':
        dl = read_setting('demo_link')
        t = f"🔥 <b>Demo Content:</b>\n👉 {dl}" if dl else "Currently demo not available."
        await query.message.reply_text(t, parse_mode='HTML')

    elif query.data == 'menu_how':
        await query.message.reply_text(read_setting('how_to_text'), parse_mode='HTML')
    
    elif query.data.startswith('cat_'):
        cat_id = int(query.data.split('_')[1])
        conn = sqlite3.connect('bot_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM categories WHERE id = ?', (cat_id,))
        cat = cursor.fetchone()
        conn.close()
        
        if not cat: return

        price = cat['price']
        upi_pa = read_setting('upi_pa').strip()
        upi_pn = read_setting('upi_pn').strip()
        
        upi_string = f"upi://pay?pa={upi_pa}&pn={urllib.parse.quote(upi_pn)}&am={price}&cu=INR"
        encoded_upi = urllib.parse.quote_plus(upi_string)
        
        # 🟢 ULTRA-SCANNABLE QR CODE API SETTINGS 🟢
        # size=500 (Bada QR), margin=3 (White border), ecLevel=L (Low density, easy to scan)
        dynamic_qr_url = f"https://quickchart.io/qr?text={encoded_upi}&size=500&margin=3&ecLevel=L"
        
        final_intent_url = INTENT_API_BASE.replace("{am}", str(price))
        
        pay_msg = (
            f"<b>💸 𝐔𝐏𝐈 𝐒𝐄𝐂𝐔𝐑𝐄 𝐏𝐀𝐘𝐌𝐄𝐍𝐓</b>\n\n"
            f"🎬 Category: <b>{cat['name']}</b>\n"
            f"🔥 𝐀𝐦𝐨𝐮𝐧𝐭: <b>₹{price}</b>\n\n"
            f"🆔 UPI ID: <code>{upi_pa}</code> <i>(Tap to Copy)</i>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👇 <b>Scan QR or PAY NOW for direct app.</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<i>(After payment, send Screenshot below)</i>"
        )
        
        pay_buttons = [
            [InlineKeyboardButton("🚀 PAY NOW (Open App)", url=final_intent_url)],
            [InlineKeyboardButton("✅ PAYMENT DONE", callback_data='payment_done')]
        ]
        
        try:
            await query.message.reply_photo(
                photo=dynamic_qr_url, 
                caption=pay_msg, 
                reply_markup=InlineKeyboardMarkup(pay_buttons), 
                parse_mode='HTML'
            )
        except Exception as e:
            logging.error(f"QR Error: {e}")
            await query.message.reply_text(f"{pay_msg}\n\n⚠️ QR load error, use UPI ID directly.", reply_markup=InlineKeyboardMarkup(pay_buttons), parse_mode='HTML')

    elif query.data == 'payment_done':
        await query.message.reply_text("📸 Please send payment <b>Screenshot</b> here for verification.", parse_mode='HTML')

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        user = update.effective_user
        keyboard = [[InlineKeyboardButton("✅ APPROVE", callback_data=f"app_{user.id}"), InlineKeyboardButton("❌ DECLINE", callback_data=f"dec_{user.id}")]]
        await context.bot.send_photo(chat_id=STATIC_ADMIN_ID, photo=update.message.photo[-1].file_id, caption=f"📩 <b>NEW PAYMENT SCREENSHOT</b>\nFrom: {user.first_name}\nID: <code>{user.id}</code>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        await update.message.reply_text("⏳ <b>𝐒𝐜𝐫𝐞𝐞𝐧𝐬𝐡𝐨𝐭 𝐒𝐞𝐧𝐭!</b> Admin is verifying.", parse_mode='HTML')

# --- 👑 ADMIN COMMANDS 👑 ---

async def cmd_allcommand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != STATIC_ADMIN_ID: return
    text = """👑 <b>ADMIN COMMANDS LIST</b>
/stats - Check Button IDs
/set_paid_link [Link] - Premium Link (Sent on Approve)
/set_price [ID]|[Price] - Change Price
/rename_button [ID]|[Naya Naam] - Button ka text badlein
/add_category [Name]|[Price]|[URL]|[Desc] - Naya Button banayein
/del_category [ID] - Button delete karein
/set_start_img [URL] - Pehli Photo
/set_prem_img [URL] - Dusri Photo
/set_start_text [Text] - Pehla Message
/set_prem_text [Text] - Dusra Message (Leave empty to remove)
/set_how_text [Text] - 'How to Get Premium' Message badlein
/set_upi [ID]|[Name] - Change UPI
/demoon [Link] - Start Demo
/demooff - Stop Demo"""
    await update.message.reply_text(text, parse_mode='HTML')

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != STATIC_ADMIN_ID: return
    conn = sqlite3.connect('bot_data.db')
    count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    cats = conn.execute('SELECT id, name, price FROM categories').fetchall()
    conn.close()
    
    paid_link = read_setting('paid_link')
    
    t = f"📊 Users: {count}\n\n🔗 Current Premium Link: {paid_link}\n\n🎬 <b>Category IDs (to change price/name):</b>\n" + "\n".join([f"ID: {c[0]} | {c[1]} - ₹{c[2]}" for c in cats])
    await update.message.reply_text(t, parse_mode='HTML')

async def cmd_rename_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != STATIC_ADMIN_ID: return
    try:
        args = update.message.text.split(' ', 1)[1].split('|')
        c_id = int(args[0].strip())
        new_name = args[1].strip()
        conn = sqlite3.connect('bot_data.db')
        conn.execute('UPDATE categories SET name = ? WHERE id = ?', (new_name, c_id))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ ID {c_id} button renamed to '{new_name}'")
    except Exception as e:
        await update.message.reply_text("Usage: /rename_button ID|Naya Naam (e.g. /rename_button 1|🔥 Premium Desi)")

async def cmd_add_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != STATIC_ADMIN_ID: return
    try:
        data = update.message.text.split(' ', 1)[1].split('|')
        conn = sqlite3.connect('bot_data.db')
        conn.execute('INSERT INTO categories (name, price, img_url, description) VALUES (?, ?, ?, ?)', (data[0].strip(), int(data[1].strip()), data[2].strip(), data[3].strip()))
        conn.commit()
        conn.close()
        await update.message.reply_text("✅ Naya Button Add Ho Gaya!")
    except:
        await update.message.reply_text("Usage: /add_category Name|Price|Img_URL|Desc")

async def cmd_del_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != STATIC_ADMIN_ID: return
    try:
        c_id = int(update.message.text.split(' ')[1])
        conn = sqlite3.connect('bot_data.db')
        conn.execute('DELETE FROM categories WHERE id = ?', (c_id,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ Button ID {c_id} Delete Ho Gaya!")
    except:
        await update.message.reply_text("Usage: /del_category ID")

async def cmd_set_paid_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != STATIC_ADMIN_ID: return
    try:
        link = update.message.text.split(' ', 1)[1]
        write_setting('paid_link', link)
        await update.message.reply_text(f"✅ Premium Link Updated to:\n{link}")
    except:
        await update.message.reply_text("Usage: /set_paid_link https://t.me/link")

async def cmd_set_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != STATIC_ADMIN_ID: return
    try:
        args = update.message.text.split(' ', 1)[1].split('|')
        c_id = int(args[0].strip())
        new_price = int(args[1].strip())
        conn = sqlite3.connect('bot_data.db')
        conn.execute('UPDATE categories SET price = ? WHERE id = ?', (new_price, c_id))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ ID {c_id} price updated to ₹{new_price}")
    except Exception as e:
        await update.message.reply_text("Usage: /set_price ID|Price")

async def cmd_set_start_img(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != STATIC_ADMIN_ID: return
    try:
        url = update.message.text.split(' ', 1)[1]
        write_setting('start_image', url)
        await update.message.reply_text("✅ Start Image Updated!")
    except: pass

async def cmd_set_prem_img(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != STATIC_ADMIN_ID: return
    try:
        url = update.message.text.split(' ', 1)[1]
        write_setting('premium_image', url)
        await update.message.reply_text("✅ Premium Image Updated!")
    except: pass

async def cmd_set_start_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != STATIC_ADMIN_ID: return
    try:
        text = update.message.text.split(' ', 1)[1]
        write_setting('start_text', text)
        await update.message.reply_text("✅ Start Text Updated!")
    except: pass

async def cmd_set_prem_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != STATIC_ADMIN_ID: return
    try:
        text = update.message.text.split(' ', 1)[1]
        write_setting('premium_text', text)
        await update.message.reply_text("✅ Premium Text Updated!")
    except: pass

async def cmd_set_how_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != STATIC_ADMIN_ID: return
    try:
        text = update.message.text.split(' ', 1)[1]
        write_setting('how_to_text', text)
        await update.message.reply_text("✅ 'How to get Premium' Text Updated!")
    except:
        await update.message.reply_text("Usage: /set_how_text Naya Text Yaha Likhein")

async def cmd_set_upi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != STATIC_ADMIN_ID: return
    try:
        args = update.message.text.split(' ', 1)[1].split('|')
        write_setting('upi_pa', args[0].strip())
        write_setting('upi_pn', args[1].strip())
        await update.message.reply_text("✅ UPI Updated!")
    except:
        await update.message.reply_text("Usage: /set_upi ID|Name")

async def cmd_demoon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != STATIC_ADMIN_ID: return
    try:
        link = update.message.text.split(' ', 1)[1]
        write_setting('demo_link', link)
        await update.message.reply_text(f"✅ Demo ON: {link}")
    except:
        await update.message.reply_text("Usage: /demoon https://t.me/link")

async def cmd_demooff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != STATIC_ADMIN_ID: return
    write_setting('demo_link', '')
    await update.message.reply_text("✅ Demo OFF")

def main():
    init_db()
    app = Application.builder().token(STATIC_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("allcommand", cmd_allcommand))
    app.add_handler(CommandHandler("stats", stats))
    
    app.add_handler(CommandHandler("set_price", cmd_set_price))
    app.add_handler(CommandHandler("rename_button", cmd_rename_button))
    app.add_handler(CommandHandler("add_category", cmd_add_category))
    app.add_handler(CommandHandler("del_category", cmd_del_category))
    app.add_handler(CommandHandler("set_paid_link", cmd_set_paid_link))
    app.add_handler(CommandHandler("set_start_img", cmd_set_start_img))
    app.add_handler(CommandHandler("set_prem_img", cmd_set_prem_img))
    app.add_handler(CommandHandler("set_start_text", cmd_set_start_text))
    app.add_handler(CommandHandler("set_prem_text", cmd_set_prem_text))
    app.add_handler(CommandHandler("set_how_text", cmd_set_how_text))
    app.add_handler(CommandHandler("set_upi", cmd_set_upi))
    app.add_handler(CommandHandler("demoon", cmd_demoon))
    app.add_handler(CommandHandler("demooff", cmd_demooff))
    
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons))
    app.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))
    
    print("Bot is LIVE! 100% same code. Both keyboards active with a single dot trick.")
    app.run_polling()

if __name__ == '__main__':
    main()
