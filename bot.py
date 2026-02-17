import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# ========== المفاتيح ==========
BOT_TOKEN = "8592275261:AAHcNEDkoc4DgRfs4IOpIDhtPUG5nsoK3xk"
GEMINI_KEY = "AIzaSyDM7lz1wRTRwM_dy_RpWPRgYaG2uHPFPtI"

# تهيئة Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('models/gemini-2.0-flash')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **مرحباً بك في بوت Gemini!**\n\n"
        "✨ أرسل لي أي سؤال وسأجيبك.",
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    try:
        response = model.generate_content(user_message)
        if response and response.text:
            await update.message.reply_text(response.text)
        else:
            await update.message.reply_text("عذراً، لم أستطع الإجابة")
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)[:100]}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 بوت Gemini يعمل!")
    app.run_polling()

if __name__ == '__main__':
    main()
