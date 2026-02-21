import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import os
from datetime import datetime
from collections import defaultdict
import json
import psutil
import humanize

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

# ========== نظام الذاكرة غير المحدودة ==========
# قاموس لتخزين معرفات المستخدمين
users_db = {}

# قاموس لتخزين سياق المحادثات - ذاكرة غير محدودة
conversation_history = defaultdict(list)

# ملف لحفظ المحادثات
HISTORY_FILE = "conversations.json"

# متغيرات لمراقبة الأداء
performance_stats = {
    'total_messages_processed': 0,
    'total_api_calls': 0,
    'total_tokens_estimated': 0,
    'start_time': datetime.now(),
    'last_memory_check': datetime.now(),
    'peak_memory': 0
}

# محاولة تحميل المحادثات السابقة من ملف
try:
    if os.path.exists(HISTORY_FILE):
        file_size = os.path.getsize(HISTORY_FILE)
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            loaded_history = json.load(f)
            for key, value in loaded_history.items():
                conversation_history[int(key)] = value
        logging.info(f"✅ تم تحميل المحادثات السابقة من الملف (الحجم: {humanize.naturalsize(file_size)})")
except Exception as e:
    logging.error(f"❌ فشل تحميل المحادثات: {e}")

def get_memory_usage():
    """قياس استهلاك الذاكرة الحالي"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    # الذاكرة المستخدمة بالبايت
    rss = memory_info.rss  # الذاكرة الفعلية
    vms = memory_info.vms  # الذاكرة الافتراضية
    
    # تحديث الذروة
    global performance_stats
    if rss > performance_stats['peak_memory']:
        performance_stats['peak_memory'] = rss
    
    return {
        'rss': rss,
        'vms': vms,
        'rss_human': humanize.naturalsize(rss),
        'vms_human': humanize.naturalsize(vms),
        'percent': process.memory_percent(),
        'cpu_percent': process.cpu_percent()
    }

def estimate_conversation_size():
    """تقدير حجم المحادثات في الذاكرة"""
    total_chars = 0
    total_messages = 0
    
    for user_id, history in conversation_history.items():
        for msg in history:
            content = msg.get('content', '')
            total_chars += len(content)
            total_messages += 1
    
    # تقدير تقريبي: كل حرف ≈ 2 بايت (للنصوص العربية)
    estimated_bytes = total_chars * 2
    
    return {
        'total_messages': total_messages,
        'total_chars': total_chars,
        'estimated_bytes': estimated_bytes,
        'estimated_human': humanize.naturalsize(estimated_bytes),
        'users_count': len(conversation_history)
    }

def save_conversations():
    """حفظ المحادثات في ملف"""
    try:
        to_save = {str(k): v for k, v in conversation_history.items()}
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)
        
        file_size = os.path.getsize(HISTORY_FILE)
        logging.info(f"✅ تم حفظ المحادثات في الملف (الحجم: {humanize.naturalsize(file_size)})")
        return True
    except Exception as e:
        logging.error(f"❌ فشل حفظ المحادثات: {e}")
        return False

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
    
    if user_id == FATIMA_ID:
        welcome_text = f"🌸 **أهلاً فاطمة المطيري!** 🌸\n\nأهلاً بك!"
        await send_to_owner(context, f"🌟 فاطمة المطيري دخلت البوت")
    
    elif user_id == ABDULKHALIQ_ID:
        welcome_text = f"👋 **مرحباً عبدالخالق!** 👋"
        await send_to_owner(context, f"👤 عبدالخالق دخل البوت")
    
    elif user_id == OWNER_ID:
        # جلب معلومات الذاكرة
        memory = get_memory_usage()
        conv_stats = estimate_conversation_size()
        
        welcome_text = f"👑 **مرحباً أيها المالك!** 👑\n\n"
        welcome_text += "📊 **حالة البوت:**\n"
        welcome_text += f"💾 **الذاكرة المستخدمة:** {memory['rss_human']}\n"
        welcome_text += f"📊 **نسبة الاستخدام:** {memory['percent']:.1f}%\n"
        welcome_text += f"💬 **الرسائل المخزنة:** {conv_stats['total_messages']:,}\n"
        welcome_text += f"👥 **المستخدمين:** {conv_stats['users_count']}\n"
        welcome_text += f"📁 **حجم المحادثات:** {conv_stats['estimated_human']}\n\n"
        welcome_text += "📝 **الأوامر المتاحة:**\n"
        welcome_text += "• `/send 123456789 الرسالة` - إرسال رسالة لمستخدم\n"
        welcome_text += "• `/users` - عرض جميع المستخدمين\n"
        welcome_text += "• `/stats` - إحصائيات البوت\n"
        welcome_text += "• `/memory` - مراقبة الذاكرة بالتفصيل\n"
        welcome_text += "• `/broadcast الرسالة` - إرسال رسالة للجميع\n"
        welcome_text += "• `/clear` - مسح ذاكرة محادثتك\n"
        welcome_text += "• `/clear_all` - مسح ذاكرة الجميع\n"
        welcome_text += "• `/save` - حفظ المحادثات يدوياً"
    
    else:
        user_info = f"@{username}" if username else f"معرف {user_id}"
        await send_to_owner(
            context,
            f"🆕 **مستخدم جديد دخل البوت**\n"
            f"👤 الاسم: {user_name}\n"
            f"🆔 المعرف: {user_id}\n"
            f"📱 اليوزر: {user_info}"
        )
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض تفاصيل استهلاك الذاكرة (للمالك فقط)"""
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ هذا الأمر للمالك فقط!")
        return
    
    # معلومات الذاكرة الحالية
    memory = get_memory_usage()
    conv_stats = estimate_conversation_size()
    
    # وقت التشغيل
    uptime = datetime.now() - performance_stats['start_time']
    uptime_str = str(uptime).split('.')[0]  # إزالة الجزء العشري
    
    # معلومات إضافية
    process = psutil.Process(os.getpid())
    num_threads = process.num_threads()
    connections = len(process.connections())
    
    # معلومات النظام
    system_memory = psutil.virtual_memory()
    
    memory_text = f"**📊 مراقبة الذاكرة بالتفصيل**\n\n"
    memory_text += f"⏱️ **وقت التشغيل:** {uptime_str}\n"
    memory_text += f"🔄 **عدد الرسائل المعالجة:** {performance_stats['total_messages_processed']:,}\n"
    memory_text += f"🌐 **استدعاءات API:** {performance_stats['total_api_calls']:,}\n\n"
    
    memory_text += f"**💾 ذاكرة البوت:**\n"
    memory_text += f"• **المستخدمة (RSS):** `{memory['rss_human']}`\n"
    memory_text += f"• **الافتراضية (VMS):** `{memory['vms_human']}`\n"
    memory_text += f"• **نسبة الاستخدام:** `{memory['percent']:.2f}%`\n"
    memory_text += f"• **الذروة:** `{humanize.naturalsize(performance_stats['peak_memory'])}`\n"
    memory_text += f"• **وحدة المعالجة:** `{memory['cpu_percent']:.1f}%`\n\n"
    
    memory_text += f"**📁 بيانات المحادثات:**\n"
    memory_text += f"• **المستخدمين:** `{conv_stats['users_count']}`\n"
    memory_text += f"• **الرسائل:** `{conv_stats['total_messages']:,}`\n"
    memory_text += f"• **حجم تقريبي:** `{conv_stats['estimated_human']}`\n"
    memory_text += f"• **متوسط لكل مستخدم:** `{conv_stats['total_messages']/max(1, conv_stats['users_count']):.1f}` رسالة\n\n"
    
    memory_text += f"**🖥️ معلومات النظام:**\n"
    memory_text += f"• **الذاكرة الكلية:** `{humanize.naturalsize(system_memory.total)}`\n"
    memory_text += f"• **المتاحة:** `{humanize.naturalsize(system_memory.available)}`\n"
    memory_text += f"• **نسبة النظام:** `{system_memory.percent}%`\n"
    memory_text += f"• **عدد الخيوط:** `{num_threads}`\n"
    memory_text += f"• **الاتصالات:** `{connections}`\n\n"
    
    memory_text += f"**💡 نصائح:**\n"
    if memory['percent'] > 80:
        memory_text += f"⚠️ **تحذير:** استهلاك الذاكرة مرتفع! استخدم `/clear_all` لتفريغ الذاكرة\n"
    elif memory['percent'] > 50:
        memory_text += f"📌 استهلاك الذاكرة متوسط، يمكنك مراقبته\n"
    else:
        memory_text += f"✅ استهلاك الذاكرة منخفض، البوت يعمل بكفاءة\n"
    
    # إرسال الرسالة
    await update.message.reply_text(memory_text, parse_mode='Markdown')
    
    # إرسال رسالة تحذير إذا كان الاستهلاك عالي
    if memory['percent'] > 90:
        await send_to_owner(
            context,
            f"⚠️ **تحذير خطير: استهلاك الذاكرة مرتفع جداً!**\n"
            f"الاستهلاك: {memory['percent']:.1f}%\n"
            f"المستخدم: {memory['rss_human']}\n"
            f"يرجى التفكير في مسح الذاكرة باستخدام /clear_all"
        )

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض جميع المستخدمين مع استهلاك كل منهم"""
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ هذا الأمر للمالك فقط!")
        return
    
    if not users_db:
        await update.message.reply_text("📭 لا يوجد مستخدمين حتى الآن.")
        return
    
    # حساب إجمالي استهلاك الذاكرة
    memory = get_memory_usage()
    
    message = f"**📋 قائمة المستخدمين** (إجمالي الذاكرة: {memory['rss_human']})\n\n"
    
    # ترتيب المستخدمين حسب عدد الرسائل (تنازلي)
    users_with_stats = []
    for uid, info in users_db.items():
        conv_length = len(conversation_history.get(uid, []))
        users_with_stats.append((uid, info, conv_length))
    
    users_with_stats.sort(key=lambda x: x[2], reverse=True)
    
    for uid, info, conv_length in users_with_stats:
        username = f"@{info['username']}" if info['username'] else "لا يوجد"
        
        # تقدير استهلاك هذا المستخدم
        user_estimated_size = 0
        if uid in conversation_history:
            user_chars = sum(len(msg.get('content', '')) for msg in conversation_history[uid])
            user_estimated_size = user_chars * 2
        
        message += f"• **{info['name']}**\n"
        message += f"  🆔 `{uid}`\n"
        message += f"  📱 {username}\n"
        message += f"  💬 رسائل: {conv_length}\n"
        if user_estimated_size > 0:
            message += f"  💾 حجم: {humanize.naturalsize(user_estimated_size)}\n"
        message += f"  🕐 {info['first_seen']}\n\n"
        
        # إذا كانت الرسالة طويلة، أرسلها وابدأ رسالة جديدة
        if len(message) > 3500:
            await update.message.reply_text(message, parse_mode='Markdown')
            message = ""
    
    if message:
        await update.message.reply_text(message, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات البوت"""
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ هذا الأمر للمالك فقط!")
        return
    
    memory = get_memory_usage()
    conv_stats = estimate_conversation_size()
    uptime = datetime.now() - performance_stats['start_time']
    uptime_str = str(uptime).split('.')[0]
    
    stats_text = f"**📊 إحصائيات البوت الشاملة**\n\n"
    stats_text += f"⏱️ **مدة التشغيل:** {uptime_str}\n"
    stats_text += f"👥 **إجمالي المستخدمين:** {len(users_db)}\n"
    stats_text += f"💬 **إجمالي الرسائل:** {conv_stats['total_messages']:,}\n"
    stats_text += f"📝 **المحادثات النشطة:** {conv_stats['users_count']}\n"
    stats_text += f"📊 **متوسط الرسائل لكل مستخدم:** {conv_stats['total_messages']/max(1, len(users_db)):.1f}\n\n"
    
    stats_text += f"**💾 استهلاك الموارد:**\n"
    stats_text += f"• **ذاكرة البوت:** {memory['rss_human']}\n"
    stats_text += f"• **نسبة الاستخدام:** {memory['percent']:.1f}%\n"
    stats_text += f"• **الذروة:** {humanize.naturalsize(performance_stats['peak_memory'])}\n"
    stats_text += f"• **الملف المحفوظ:** {humanize.naturalsize(os.path.getsize(HISTORY_FILE)) if os.path.exists(HISTORY_FILE) else 'لا يوجد'}\n\n"
    
    stats_text += f"**⚡ الأداء:**\n"
    stats_text += f"• **رسائل معالجة:** {performance_stats['total_messages_processed']:,}\n"
    stats_text += f"• **استدعاءات API:** {performance_stats['total_api_calls']:,}\n"
    stats_text += f"• **المعدل:** {performance_stats['total_messages_processed'] / max(1, uptime.total_seconds() / 3600):.1f} رسالة/ساعة\n"
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def send_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال رسالة لمستخدم معين (للمالك فقط)"""
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ هذا الأمر للمالك فقط!")
        return
    
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
        
        success = await send_to_user(context, target_id, message)
        
        if success:
            await update.message.reply_text(f"✅ تم إرسال الرسالة بنجاح إلى `{target_id}`", parse_mode='Markdown')
            
            # حفظ الرسالة في ذاكرة المستخدم
            conversation_history[target_id].append({"role": "assistant", "content": message})
            performance_stats['total_messages_processed'] += 1
            
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
        if uid != OWNER_ID:
            if await send_to_user(context, uid, message):
                success_count += 1
                conversation_history[uid].append({"role": "assistant", "content": message})
                performance_stats['total_messages_processed'] += 1
            else:
                fail_count += 1
    
    await update.message.reply_text(
        f"✅ **تم الإرسال:** {success_count}\n"
        f"❌ **فشل:** {fail_count}"
    )

async def clear_memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مسح ذاكرة المستخدم الحالي"""
    user_id = update.effective_user.id
    
    if user_id in conversation_history:
        # حساب حجم الذاكرة قبل المسح
        old_size = sum(len(msg.get('content', '')) for msg in conversation_history[user_id]) * 2
        
        conversation_history[user_id] = []
        
        memory = get_memory_usage()
        await update.message.reply_text(
            f"🧹 **تم مسح ذاكرتك بنجاح!**\n"
            f"تم تحرير حوالي {humanize.naturalsize(old_size)}\n"
            f"الذاكرة الحالية: {memory['rss_human']}",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("لا يوجد محادثات سابقة لمسحها.")

async def clear_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مسح ذاكرة جميع المستخدمين (للمالك فقط)"""
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ هذا الأمر للمالك فقط!")
        return
    
    # حساب حجم الذاكرة قبل المسح
    memory_before = get_memory_usage()
    conv_stats_before = estimate_conversation_size()
    
    conversation_history.clear()
    performance_stats['total_messages_processed'] = 0
    
    memory_after = get_memory_usage()
    
    await update.message.reply_text(
        f"🧹 **تم مسح ذاكرة الجميع!**\n"
        f"قبل: {memory_before['rss_human']} | بعد: {memory_after['rss_human']}\n"
        f"تم تحرير: {humanize.naturalsize(memory_before['rss'] - memory_after['rss'])}\n"
        f"تم حذف {conv_stats_before['total_messages']} رسالة",
        parse_mode='Markdown'
    )
    
    await send_to_owner(context, f"🗑️ تم مسح ذاكرة جميع المستخدمين")

async def save_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حفظ المحادثات يدوياً (للمالك فقط)"""
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ هذا الأمر للمالك فقط!")
        return
    
    if save_conversations():
        file_size = os.path.getsize(HISTORY_FILE)
        memory = get_memory_usage()
        await update.message.reply_text(
            f"💾 **تم حفظ المحادثات!**\n"
            f"حجم الملف: {humanize.naturalsize(file_size)}\n"
            f"الذاكرة الحالية: {memory['rss_human']}",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ فشل حفظ المحادثات!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    user_name = update.message.from_user.first_name
    username = update.message.from_user.username

    # تحديث الإحصائيات
    performance_stats['total_messages_processed'] += 1

    # تخزين المستخدم إذا كان جديد
    if user_id not in users_db and user_id != OWNER_ID:
        users_db[user_id] = {
            'name': user_name,
            'username': username,
            'first_seen': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    try:
        # بناء قائمة الرسائل مع كل المحادثة السابقة
        messages = [
            {"role": "system", "content": "أنت مساعد ذكي. رد بالعربية فقط. لديك ذاكرة غير محدودة، تذكر كل المحادثة السابقة بالكامل واستمر في السياق."}
        ]
        
        # إضافة كل المحادثة السابقة
        for old_msg in conversation_history[user_id]:
            messages.append(old_msg)
        
        # إضافة الرسالة الجديدة
        messages.append({"role": "user", "content": user_message})
        
        # حفظ رسالة المستخدم في التاريخ
        conversation_history[user_id].append({"role": "user", "content": user_message})
        
        performance_stats['total_api_calls'] += 1
        performance_stats['total_tokens_estimated'] += len(user_message) // 2  # تقدير تقريبي
        
        logging.info(f"📝 إرسال {len(messages)} رسالة إلى الذكاء الاصطناعي للمستخدم {user_id}")
        
        # فحص الذاكرة كل 10 رسائل
        if performance_stats['total_messages_processed'] % 10 == 0:
            memory = get_memory_usage()
            if memory['percent'] > 80:
                await send_to_owner(
                    context,
                    f"⚠️ **تنبيه: استهلاك الذاكرة {memory['percent']:.1f}%**\n"
                    f"المستخدم: {memory['rss_human']}\n"
                    f"الرسائل المخزنة: {estimate_conversation_size()['total_messages']}"
                )
        
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
                "messages": messages,
                "temperature": 0.3
            },
            timeout=60
        )
        
        data = response.json()
        
        if response.status_code == 200:
            reply = data['choices'][0]['message']['content']
            await update.message.reply_text(reply)
            
            # حفظ رد البوت في التاريخ
            conversation_history[user_id].append({"role": "assistant", "content": reply})
            
            # حفظ في الملف كل 20 رسالة
            if performance_stats['total_messages_processed'] % 20 == 0:
                save_conversations()
            
            # إرسال نسخة للمالك عن كل المحادثات
            if user_id != OWNER_ID:
                user_info = f"@{username}" if username else f"معرف {user_id}"
                
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
                    f"💬 **طول المحادثة:** {len(conversation_history[user_id])//2} جولات\n"
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
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("memory", memory_command))
    app.add_handler(CommandHandler("send", send_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("clear", clear_memory_command))
    app.add_handler(CommandHandler("clear_all", clear_all_command))
    app.add_handler(CommandHandler("save", save_command))
    
    # معالج الرسائل العادية
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # معلومات بدء التشغيل
    memory = get_memory_usage()
    conv_stats = estimate_conversation_size()
    
    print("=" * 70)
    print("🤖 البوت يعمل مع ذاكرة غير محدودة ونظام مراقبة!")
    print("=" * 70)
    print(f"💾 **الذاكرة الحالية:** {memory['rss_human']} ({memory['percent']:.1f}%)")
    print(f"📊 **الرسائل المخزنة:** {conv_stats['total_messages']:,}")
    print(f"👥 **المستخدمين النشطين:** {conv_stats['users_count']}")
    print(f"📁 **حجم المحادثات:** {conv_stats['estimated_human']}")
    print("=" * 70)
    print("✅ الأشخاص المميزون:")
    print(f"   • فاطمة المطيري (ID: {FATIMA_ID})")
    print(f"   • عبدالخالق (ID: {ABDULKHALIQ_ID})")
    print("=" * 70)
    print("📝 **أوامر المراقبة:**")
    print("   • `/memory` - مراقبة الذاكرة بالتفصيل")
    print("   • `/stats` - إحصائيات شاملة")
    print("   • `/users` - قائمة المستخدمين مع استهلاك كل منهم")
    print("=" * 70)
    
    # حفظ المحادثات عند إيقاف البوت
    try:
        app.run_polling()
    finally:
        save_conversations()
        memory = get_memory_usage()
        print(f"💾 تم حفظ جميع المحادثات. الذاكرة النهائية: {memory['rss_human']}")

if __name__ == '__main__':
    # تأكد من تثبيت المكتبات الإضافية
    # pip install psutil humanize
    main()
