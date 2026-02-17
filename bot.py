import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import os

# ========== قراءة المفاتيح من Environment Variables ==========
BOT_TOKEN = os.environ.get('BOT_TOKEN')
OPENROUTER_KEY = os.environ.get('OPENROUTER_KEY')

if not BOT_TOKEN or not OPENROUTER_KEY:
    raise ValueError("❌ المفاتيح غير موجودة في Environment Variables!")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ========== المعرفات ==========
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
    
    await update.message.reply_text(
        "👋 **مرحباً بك في بوت الذكاء الاصطناعي!**\n\n"
        "✨ أرسل لي أي سؤال وسأجيبك بالعربية.",
        parse_mode='Markdown'
    )
    
    if user_id == ABRAR_ID:
        await send_to_owner(context, f"🌟 أبرار دخلت البوت!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    user_name = update.message.from_user.first_name

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    try:
        # ✅ النظام الجديد - يطلب العربية فقط
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://t.me/your_bot",
                "X-Title": "Telegram Bot"
            },
            json={
                "model": "meta-llama/llama-3-8b-instruct",
                "messages": [
                    {"role": "system", "content": "أنت مساعد ذكي. يجب أن ترد باللغة العربية الفصحى فقط. لا تستخدم أي لغة أخرى مهما كان السؤال. حتى إذا سأل المستخدم بالإنجليزية، رد بالعربية."},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.3  # درجة حرارة منخفضة = ردود أكثر دقة
            },
            timeout=30
        )
        
        data = response.json()
        
        if response.status_code == 200:
            reply = data['choices'][0]['message']['content']
            await update.message.reply_text(reply)
            
            if user_id == ABRAR_ID:
                await send_to_owner(
                    context,
                    f"📩 **أبرار**\n"
                    f"💬 {user_message[:50]}...\n"
                    f"🤖 {reply[:50]}..."
                )
        else:
            error_msg = data.get('error', {}).get('message', 'خطأ غير معروف')
            await update.message.reply_text(f"❌ خطأ: {error_msg}")
            
    except Exception as e:
        logging.error(f"خطأ: {e}")
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)[:100]}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("=" * 50)
    print("🤖 البوت يعمل - ردود عربية فقط")
    print("=" * 50)
    
    app.run_polling()

if __name__ == '__main__':
    main()
