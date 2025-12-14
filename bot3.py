import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from collections import defaultdict, deque
import aiohttp
import json
from datetime import datetime

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = "8226914699:AAH0zswa7e9BSmBg-pedtSxNb2xlYeuz6hI"

# Конфигурация вашего Cloud AI API
API_BASE_URL = "https://agent.timeweb.cloud/api/v1/cloud-ai/agents"
AGENT_ACCESS_ID = "f01ca76e-2513-489f-a2ce-39296f832857"
long_token ="eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCIsImtpZCI6IjFrYnhacFJNQGJSI0tSbE1xS1lqIn0.eyJ1c2VyIjoiaGgyNDM5NiIsInR5cGUiOiJhcGlfa2V5IiwiYXBpX2tleV9pZCI6Ijk4OTM1ZTIwLWNhNTktNDEwMy1hMTY0LTZlNjhkZjk2ZmVlYSIsImlhdCI6MTc2NTQ2MzAyM30.HXR7jvXknl0kr7voaB8RrYsQLTi5mNrH00FeG9ZJqRGxmISZKAVBQpKDmt7vB3X2I20vcaNwKji5jP343IGqpAHlbGCfcDYLKMjzoIYJFCEvNJmGX7qMgoC5UxNFCH8zfqfV6VmXzmGMdL3u2cfrdJ_FE_ocwA1Q3wTA52Q5knhTRsgYUxP79oIStrgxzm_Fwtls5Lo94ROKdg8meaX5hvzDielFR6-E9kX4XPGsIA5K0aLghBaZvgU0Tq8_STatZ7sa-zja4PZ_Km-ZP9TUSy51K6YNiS_K5bzFUsOo166UKkEsalTmhpinBMhkoipNR8KMmHCWr4ZTH-hhy_2NLDWSAef8Nc6LQd-o7uuNn6T0T_HT6wqonBpbbfCi1WGAEz44788clcJpqhWHLdyXmjVLw5DSZeGyXM0TJaTQ42EP4F6vLyhYgrjURErt6Ge0F078zgsHY18kuVWUJsg_OkoYFWAu6cRer544EehhAmNYJF-GrczA6pcWP8U9S7pJ"
# ID создателя (ваш)
CREATOR_ID = 44643863  # Ваш ID @morison_son

# Список авторизованных пользователей (ID, имя, username)
AUTHORIZED_USERS = {
    301232059: {"first_name": "Екатерина", "username": "RybakovaKaterina", "last_name": "Рыбакова"},
    44643863: {"first_name": "Ilya", "username": "morison_son", "last_name": "Kopyt"},
    7262688484: {"first_name": "Илья", "username": "po_ilia", "last_name": "Копыт"}
}

# ==================== ХРАНЕНИЕ КОНТЕКСТА ====================
# Храним историю диалогов для каждого пользователя (user_id -> deque)
user_contexts = defaultdict(lambda: deque(maxlen=10))

# Храним историю публичных сообщений от создателя (для всех пользователей)
public_messages = deque(maxlen=50)  # Храним последние 50 публичных сообщений

def get_context_for_user(user_id):
    """Возвращает историю сообщений пользователя в формате для API"""
    history = list(user_contexts[user_id])
    
    if history:
        return history
    
    # Системное сообщение для авторизованных пользователей
    if user_id in AUTHORIZED_USERS or user_id == CREATOR_ID:
        return [
            {"role": "system", "content": "Ты полезный AI-ассистент. Отвечай на русском языке."}
        ]
    else:
        return [
            {"role": "system", "content": "Ты полезный AI-ассистент. Я не знаю твоего ID, поэтому могу отвечать только на общие вопросы."}
        ]

def add_to_context(user_id, role, content):
    """Добавляет сообщение в контекст пользователя"""
    user_contexts[user_id].append({"role": role, "content": content})

def clear_context(user_id):
    """Очищает контекст пользователя"""
    if user_id in user_contexts:
        user_contexts[user_id].clear()
    
    if user_id in AUTHORIZED_USERS or user_id == CREATOR_ID:
        user_contexts[user_id].append({
            "role": "system", 
            "content": "Ты полезный AI-ассистент. Отвечай на русском языке."
        })
    else:
        user_contexts[user_id].append({
            "role": "system", 
            "content": "Ты полезный AI-ассистент. Я не знаю твоего ID, поэтому могу отвечать только на общие вопросы."
        })

def add_public_message(sender_name, message):
    """Добавляет публичное сообщение от создателя"""
    timestamp = datetime.now().strftime("%H:%M")
    public_messages.append({
        "timestamp": timestamp,
        "sender": sender_name,
        "message": message
    })

def get_recent_public_messages(limit=10):
    """Возвращает последние публичные сообщения"""
    return list(public_messages)[-limit:]

# ==================== ИНТЕГРАЦИЯ С CLOUD AI API ====================
async def call_cloud_ai_api(user_id, user_message):
    """
    Отправляет запрос к вашему Cloud AI API
    Использует OpenAI-совместимый эндпоинт /v1/chat/completions
    """
    # Добавляем сообщение пользователя в контекст
    add_to_context(user_id, "user", user_message)
    
    # Получаем текущий контекст (последние 10 сообщений)
    messages = get_context_for_user(user_id)
    
    # Формируем URL для запроса
    #curl 'https://agent.timeweb.cloud/api/v1/cloud-ai/agents/{agent_access_id}/v1/chat/completions' \

    #url = f"{API_BASE_URL}/{AGENT_ACCESS_ID}/v1/chat/completions"
    url=f'https://agent.timeweb.cloud/api/v1/cloud-ai/agents/f01ca76e-2513-489f-a2ce-39296f832857/v1/chat/completions' \

    
   # ФОРМИРУЕМ ЗАГОЛОВКИ С BEARER-ТОКЕНОМ согласно документации[citation:3][citation:6]
    headers = {
        "Content-Type": "application/json",
        "x-proxy-source": "telegram-bot",
        "Authorization": f"Bearer {long_token}"  # ⬅️ Ключевое исправление
    }
    
    # Формируем тело запроса
    payload = {
        "messages": messages,
        "model": "gpt-4",
        "temperature": 0.7,
        "max_completion_tokens": 1000,
        "stream": False
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    ai_response = data["choices"][0]["message"]["content"]
                    add_to_context(user_id, "assistant", ai_response)
                    return ai_response, data.get("usage", {})
                else:
                    error_text = await response.text()
                    logging.error(f"API error {response.status}: {error_text}")
                    return f"❌ Ошибка API ({response.status})", {}
                    
    except Exception as e:
        logging.error(f"Request failed: {e}")
        return f"⚠️ Ошибка соединения с AI", {}

# ==================== КОМАНДЫ ТЕЛЕГРАМ-БОТА ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    user_id = user.id
    
    # Инициализируем контекст
    if user_id not in user_contexts or len(user_contexts[user_id]) == 0:
        clear_context(user_id)
    
    # Проверяем авторизацию
    if user_id == CREATOR_ID:
        user_type = "👑 СОЗДАТЕЛЬ"
        permissions = "• Личный чат с AI\n• Публичные сообщения для всех\n• Просмотр статуса"
    elif user_id in AUTHORIZED_USERS:
        user_type = "✅ АВТОРИЗОВАННЫЙ ПОЛЬЗОВАТЕЛЬ"
        permissions = "• Личный чат с AI\n• Чтение публичных сообщений\n• Просмотр статуса"
    else:
        user_type = "👤 ГОСТЬ"
        permissions = "• Ограниченный доступ"
    
    welcome_text = f"""
🤖 Привет, {user.first_name}!

{user_type}

📋 Доступные функции:
{permissions}

💬 Просто напишите сообщение для личного диалога с AI

"""
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    user_id = update.effective_user.id
    
    help_text = """
📚 Общие команды:

/start - Информация о боте
/help - Эта справка  
/status - Статус системы
/public - Читать публичные сообщения

"""
    
    if user_id == CREATOR_ID:
        help_text += """
👑 Команды создателя:

• Просто напишите сообщение с текстом - оно будет отправлено всем как публичное
• Добавьте "//" в начале для личного общения с AI
Пример: "//привет" - лично AI, "привет" - публично всем

📋 Примеры:
"Всем привет!" - публичное сообщение
"//Как дела?" - личный вопрос AI
"""
    elif user_id in AUTHORIZED_USERS:
        help_text += """
✅ Ваши возможности:

• Любое сообщение - личный диалог с AI
• /new - очистить историю диалога
• /public - читать публичные сообщения
"""
    else:
        help_text += """
👤 Гостевой доступ:

Вы можете использовать только общие команды.
Для полного доступа обратитесь к создателю.
"""
    
    await update.message.reply_text(help_text)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /status - информация о системе"""
    user_id = update.effective_user.id
    
    # Считаем активных пользователей
    active_users = len([uid for uid in user_contexts if len(user_contexts[uid]) > 0])
    public_count = len(public_messages)
    
    status_text = f"""
📊 Статус системы:
━━━━━━━━━━━━━━━━
👥 Всего пользователей: {len(user_contexts)}
💬 Активных диалогов: {active_users}
📢 Публичных сообщений: {public_count}
━━━━━━━━━━━━━━━━
"""
    
    # Добавляем информацию о правах
    if user_id == CREATOR_ID:
        status_text += f"""
👑 Вы: СОЗДАТЕЛЬ (ID: {user_id})
━━━━━━━━━━━━━━━━
✅ Авторизованные пользователи:
"""
        for uid, info in AUTHORIZED_USERS.items():
            status_text += f"• {info['first_name']} (@{info['username']})\n"
    
    elif user_id in AUTHORIZED_USERS:
        info = AUTHORIZED_USERS[user_id]
        status_text += f"\n✅ Вы авторизованы как: {info['first_name']} (@{info['username']})"
    
    else:
        status_text += f"\n👤 Вы вошли как гость (ID: {user_id})"
    
    await update.message.reply_text(status_text)

async def public_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /public - показать публичные сообщения"""
    user_id = update.effective_user.id
    
    if user_id not in AUTHORIZED_USERS and user_id != CREATOR_ID:
        await update.message.reply_text("❌ Эта команда только для авторизованных пользователей.")
        return
    
    messages = get_recent_public_messages(10)
    
    if not messages:
        await update.message.reply_text("📭 Публичных сообщений пока нет.")
        return
    
    public_text = "📢 Последние публичные сообщения:\n━━━━━━━━━━━━━━━━\n"
    
    for msg in messages:
        public_text += f"[{msg['timestamp']}] {msg['sender']}:\n{msg['message']}\n━━━━━━━━━━━━━━━━\n"
    
    # Если сообщение слишком длинное, разбиваем на части
    if len(public_text) > 4000:
        parts = [public_text[i:i+4000] for i in range(0, len(public_text), 4000)]
        for part in parts:
            await update.message.reply_text(part)
    else:
        await update.message.reply_text(public_text)

async def new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /new - очистить историю диалога"""
    user_id = update.effective_user.id
    
    if user_id not in AUTHORIZED_USERS and user_id != CREATOR_ID:
        await update.message.reply_text("❌ Эта команда только для авторизованных пользователей.")
        return
    
    clear_context(user_id)
    await update.message.reply_text("🔄 История диалога очищена! Начинаем новый разговор.")

# ==================== ОСНОВНОЙ ОБРАБОТЧИК СООБЩЕНИЙ ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главный обработчик всех текстовых сообщений"""
    user = update.effective_user
    user_id = user.id
    user_message = update.message.text
    
    # Если это команда - пропускаем (обрабатывается отдельно)
    if user_message.startswith('/'):
        return
    
    # ========== ОБРАБОТКА ДЛЯ СОЗДАТЕЛЯ ==========
    if user_id == CREATOR_ID:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, 
            action="typing"
        )
        
        # Если сообщение начинается с "//" - личный диалог с AI
        if user_message.startswith("//"):
            # Убираем "//" из начала
            ai_message = user_message[2:].strip()
            
            # Получаем ответ от AI
            ai_response, _ = await call_cloud_ai_api(user_id, ai_message)
            
            # Отправляем ответ
            await update.message.reply_text(f"🤖 AI (личный):\n{ai_response}")
            
        else:
            # ПУБЛИЧНОЕ СООБЩЕНИЕ для всех пользователей
            sender_name = f"👑 {user.first_name}"
            add_public_message(sender_name, user_message)
            
            # Уведомляем создателя
            await update.message.reply_text(
                f"✅ Публичное сообщение добавлено!\n"
                f"📝 Текст: {user_message[:100]}..."
            )
            
            # Рассылаем уведомление всем авторизованным пользователям
            notified = 0
            for uid in AUTHORIZED_USERS:
                try:
                    await context.bot.send_message(
                        chat_id=uid,
                        text=f"📢 Новое публичное сообщение от создателя!\n"
                             f"Используйте /public чтобы прочитать."
                    )
                    notified += 1
                except Exception as e:
                    logging.error(f"Не удалось уведомить {uid}: {e}")
            
            # Отчет создателю
            await update.message.reply_text(
                f"📤 Уведомления отправлены {notified}/{len(AUTHORIZED_USERS)} пользователям."
            )
    
    # ========== ОБРАБОТКА ДЛЯ АВТОРИЗОВАННЫХ ПОЛЬЗОВАТЕЛЕЙ ==========
    elif user_id in AUTHORIZED_USERS:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, 
            action="typing"
        )
        
        # Все сообщения авторизованных пользователей идут в личный чат с AI
        ai_response, _ = await call_cloud_ai_api(user_id, user_message)
        
        # Отправляем ответ
        user_info = AUTHORIZED_USERS[user_id]
        await update.message.reply_text(
            f"🤖 AI для {user_info['first_name']}:\n{ai_response}"
        )
    
    # ========== ОБРАБОТКА ДЛЯ ГОСТЕЙ ==========
    else:
        # Гости могут только получать информацию
        await update.message.reply_text(
            "❌ Доступ ограничен. Вы не авторизованы.\n"
            "Используйте /start для информации или обратитесь к создателю.\n\n"
            f"Ваш ID: {user_id}\n"
            "Сообщите этот ID создателю для получения доступа."
        )

# ==================== ЗАПУСК БОТА ====================
def main():
    """Основная функция для запуска бота"""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    # Создаём приложение бота
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("public", public_command))
    application.add_handler(CommandHandler("new", new_chat))
    
    # Регистрируем обработчик текстовых сообщений
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    
    # Запускаем бота
    print("=" * 60)
    print("🤖 Бот с системой доступа запущен!")
    print(f"👑 Создатель ID: {CREATOR_ID}")
    print("✅ Авторизованные пользователи:")
    for uid, info in AUTHORIZED_USERS.items():
        print(f"   • {info['first_name']} (@{info['username']}) - ID: {uid}")
    print("=" * 60)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()