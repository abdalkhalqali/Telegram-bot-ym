import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
import os

# ========== قراءة المفاتيح من Environment Variables (آمن) ==========
BOT_TOKEN = os.environ.get('BOT_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_KEY')

if not BOT_TOKEN or not GEMINI_KEY:
    raise ValueError("❌ المفاتيح غير موجودة في Environment Variables! أضفها في إعدادات Render.")

# تهيئة Gemini بالمكتبة الجديدة
client = genai.Client(api_key=GEMINI_KEY)

logging.basicConfig(format='%(asime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **مرحباً بك في بوت Gemini الجديد!**\n\n"
        "✨ أرسل لي أي سؤال وسأجيبك.",
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    try:
        # استخدام المكتبة الجديدة
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=user_message
        )
        if response and response.text:
            await update.message.reply_text(response.text)
        else:
            await update.message.reply_text("عذراً، لم أستطع الإجابة.")
    except Exception as e:
        logging.error(f"خطأ: {e}")
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)[:100]}")

def main():
    # إنشاء التطبيق بالمكتبة المحدثة
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 بوت Gemini الجديد يعمل!")
    app.run_polling()

if __name__ == '__main__':
    main()
