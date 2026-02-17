import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import os
from datetime import datetime

# ========== قراءة المفاتيح من Environment Variables فقط ==========
BOT_TOKEN = os.environ.get('BOT_TOKEN')
OPENROUTER_KEY = os.environ.get('OPENROUTER_KEY')

if not BOT_TOKEN or not OPENROUTER_KEY:
    raise ValueError("❌ المفاتيح غير موجودة في Environment Variables! يجب إضافتها في إعدادات Render.")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ========== المعرفات ==========
ABRAR_ID = 1406525284
ABDULKHALIQ_ID = 6818088581
OWNER_ID = 383022213

async def send_to_owner(context, text):
    """إرسال إشعار للمالك"""
    try:
        await context.bot.send_message(chat_id=OWNER_ID, text=text, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"فشل إرسال للمالك: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.message.from_user.first_name
    
    welcome_text = "👋 **مرحباً بك في بوت الذكاء الاصطناعي!**\n\n✨ أرسل لي أي سؤال وسأجيبك."
    
    if user_id == ABRAR_ID:
        welcome_text = f"🌸 **أهلاً أبرار!** 🌸\n\nأهلاً بك!"
        await send_to_owner(context, f"🌟 أبرار دخلت البوت")
    
    elif user_id == ABDULKHALIQ_ID:
        welcome_text = f"👋 **مرحباً عبدالخالق!** 👋"
        await send_to_owner(context, f"👤 عبدالخالق دخل البوت")
    
    elif user_id == OWNER_ID:
        welcome_text = f"👑 **مرحباً أيها المالك!** 👑"
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    user_name = update.message.from_user.first_name

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",  # ✅ من Environment Variables
                "Content-Type": "application/json",
                "HTTP-Referer": "https://t.me/your_bot",
                "X-Title": "Telegram Bot"
            },
            json={
                "model": "meta-llama/llama-3-8b-instruct",
                "messages": [
                    {"role": "system", "content": "أنت مساعد ذكي. رد بالعربية فقط."},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.3
            },
            timeout=30
        )
        
        data = response.json()
        
        if response.status_code == 200:
            reply = data['choices'][0]['message']['content']
            await update.message.reply_text(reply)
            
            # إرسال نسخة للمالك
            if user_id in [ABRAR_ID, ABDULKHALIQ_ID]:
                user_type = "أبرار" if user_id == ABRAR_ID else "عبدالخالق"
                await send_to_owner(
                    context,
                    f"📩 **رسالة من {user_type}**\n"
                    f"👤 {user_name}\n"
                    f"💬 {user_message[:100]}...\n"
                    f"🤖 {reply[:100]}..."
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
    print("🤖 البوت يعمل - المفاتيح من Environment Variables")
    print("=" * 50)
    print("✅ آمن تماماً - لا مفاتيح في الكود")
    print("=" * 50)
    
    app.run_polling()

if __name__ == '__main__':
    main()
