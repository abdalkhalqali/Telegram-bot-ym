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
FATIMA_ID = 1295746334  # معرف فاطمة المطيري
ABDULKHALIQ_ID = 6818088581
OWNER_ID = 383022213

# قاموس لتخزين معرفات المستخدمين الذين تواصلوا مع البوت
users_db = {}

async def send_to_owner(context, text):
    """إرسال إشعار للمالك"""
    try:
        await context.bot.send_message(chat_id=OWNER_ID, text=text, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"فشل إرسال للمالك: {e}")

async def send_to_user(context, user_id, text):
    """إرسال رسالة لمستخدم معين"""
    try:
        await context.bot.send_message(chat_id=user_id, text=text, parse_mode='Markdown')
        return True
    except Exception as e:
        logging.error(f"فشل إرسال للمستخدم {user_id}: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.message.from_user.first_name
    username = update.message.from_user.username
    
    # تخزين معلومات المستخدم
    users_db[user_id] = {
        'name': user_name,
        'username': username,
        'first_seen': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    welcome_text = "👋 **مرحباً بك في بوت الذكاء الاصطناعي!**\n\n✨ أرسل لي أي سؤال وسأجيبك."
    
    if user_id == FATIMA_ID:  # تغيير من ABRAR_ID إلى FATIMA_ID
        welcome_text = f"🌸 **أهلاً فاطمة المطيري!** 🌸\n\nأهلاً بك!"
        await send_to_owner(context, f"🌟 فاطمة المطيري دخلت البوت")
    
    elif user_id == ABDULKHALIQ_ID:
        welcome_text = f"👋 **مرحباً عبدالخالق!** 👋"
        await send_to_owner(context, f"👤 عبدالخالق دخل البوت")
    
    elif user_id == OWNER_ID:
        welcome_text = f"👑 **مرحباً أيها المالك!** 👑\n\n"
        welcome_text += "📝 **الأوامر المتاحة:**\n"
        welcome_text += "• `/send 123456789 الرسالة` - لإرسال رسالة لمستخدم\n"
        welcome_text += "• `/users` - لعرض جميع المستخدمين\n"
        welcome_text += "• `/broadcast الرسالة` - لإرسال رسالة للجميع"
    
    else:
        # إشعار للمالك بمستخدم جديد
        user_info = f"@{username}" if username else f"معرف {user_id}"
        await send_to_owner(
            context,
            f"🆕 **مستخدم جديد دخل البوت**\n"
            f"👤 الاسم: {user_name}\n"
            f"🆔 المعرف: {user_id}\n"
            f"📱 اليوزر: {user_info}"
        )
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض جميع المستخدمين (للمالك فقط)"""
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ هذا الأمر للمالك فقط!")
        return
    
    if not users_db:
        await update.message.reply_text("📭 لا يوجد مستخدمين حتى الآن.")
        return
    
    message = "**📋 قائمة المستخدمين:**\n\n"
    for uid, info in users_db.items():
        username = f"@{info['username']}" if info['username'] else "لا يوجد"
        message += f"• **{info['name']}**\n"
        message += f"  🆔 `{uid}`\n"
        message += f"  📱 {username}\n"
        message += f"  🕐 {info['first_seen']}\n\n"
    
    # تقسيم الرسالة إذا كانت طويلة
    if len(message) > 4000:
        for i in range(0, len(message), 4000):
            await update.message.reply_text(message[i:i+4000], parse_mode='Markdown')
    else:
        await update.message.reply_text(message, parse_mode='Markdown')

async def send_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال رسالة لمستخدم معين (للمالك فقط)"""
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ هذا الأمر للمالك فقط!")
        return
    
    # التحقق من وجود المعاملات
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ **استخدام غير صحيح!**\n\n"
            "✅ استخدم الأمر بهذا الشكل:\n"
            "`/send 123456789 مرحباً كيف حالك؟`\n\n"
            "ℹ️ يمكنك معرفة معرف المستخدم باستخدام الأمر /users",
            parse_mode='Markdown'
        )
        return
    
    try:
        target_id = int(context.args[0])
        message = ' '.join(context.args[1:])
        
        success = await send_to_user(context, target_id, f"📨 **رسالة من المالك:**\n\n{message}")
        
        if success:
            await update.message.reply_text(f"✅ تم إرسال الرسالة بنجاح إلى `{target_id}`", parse_mode='Markdown')
            
            # إرسال إشعار للمالك بأن الرسالة وصلت (اختياري)
            user_info = users_db.get(target_id, {})
            if user_info:
                await send_to_owner(
                    context,
                    f"📤 **تم إرسال رسالة**\n"
                    f"إلى: {user_info.get('name', 'مستخدم')}\n"
                    f"المحتوى: {message[:100]}..."
                )
        else:
            await update.message.reply_text(f"❌ فشل إرسال الرسالة إلى `{target_id}`", parse_mode='Markdown')
    
    except ValueError:
        await update.message.reply_text("❌ معرف المستخدم يجب أن يكون رقماً!")
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)}")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال رسالة لجميع المستخدمين (للمالك فقط)"""
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ هذا الأمر للمالك فقط!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ **استخدام غير صحيح!**\n\n"
            "✅ استخدم الأمر بهذا الشكل:\n"
            "`/broadcast مرحباً بالجميع!`",
            parse_mode='Markdown'
        )
        return
    
    message = ' '.join(context.args)
    
    if not users_db:
        await update.message.reply_text("📭 لا يوجد مستخدمين لإرسال الرسالة لهم.")
        return
    
    await update.message.reply_text(f"📤 جاري إرسال الرسالة إلى {len(users_db)} مستخدم...")
    
    success_count = 0
    fail_count = 0
    
    for uid in users_db.keys():
        if uid != OWNER_ID:  # لا ترسل للمالك نفسه
            if await send_to_user(context, uid, f"📢 **رسالة عامة:**\n\n{message}"):
                success_count += 1
            else:
                fail_count += 1
    
    await update.message.reply_text(
        f"✅ **تم الإرسال:** {success_count}\n"
        f"❌ **فشل:** {fail_count}"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    user_name = update.message.from_user.first_name
    username = update.message.from_user.username

    # تخزين المستخدم إذا كان جديد
    if user_id not in users_db and user_id != OWNER_ID:
        users_db[user_id] = {
            'name': user_name,
            'username': username,
            'first_seen': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    try:
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
            
            # إرسال نسخة للمالك عن كل المحادثات
            if user_id != OWNER_ID:  # لا ترسل للمالك محادثاته هو
                user_info = f"@{username}" if username else f"معرف {user_id}"
                
                # تحديد اسم المستخدم المميز
                if user_id == FATIMA_ID:
                    special_name = "فاطمة المطيري"
                elif user_id == ABDULKHALIQ_ID:
                    special_name = "عبدالخالق"
                else:
                    special_name = user_name
                
                await send_to_owner(
                    context,
                    f"📩 **محادثة جديدة**\n"
                    f"👤 الاسم: {special_name}\n"
                    f"🆔 المعرف: `{user_id}`\n"
                    f"📱 اليوزر: {user_info}\n"
                    f"💬 **السؤال:**\n{user_message[:200]}\n"
                    f"🤖 **الإجابة:**\n{reply[:200]}..."
                )
        else:
            error_msg = data.get('error', {}).get('message', 'خطأ غير معروف')
            await update.message.reply_text(f"❌ خطأ: {error_msg}")
            
    except Exception as e:
        logging.error(f"خطأ: {e}")
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)[:100]}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # أوامر المالك
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("send", send_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    
    # معالج الرسائل العادية
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("=" * 50)
    print("🤖 البوت يعمل - المفاتيح من Environment Variables")
    print("=" * 50)
    print("✅ الأشخاص المميزون:")
    print(f"   • فاطمة المطيري (ID: {FATIMA_ID})")
    print(f"   • عبدالخالق (ID: {ABDULKHALIQ_ID})")
    print("=" * 50)
    print("✅ أوامر المالك المتاحة:")
    print("   • /send [المعرف] [الرسالة]")
    print("   • /users")
    print("   • /broadcast [الرسالة]")
    print("=" * 50)
    
    app.run_polling()

if __name__ == '__main__':
    main()
