import os
import datetime
import base64
import pickle
from anthropic import Anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_TOKEN = os.getenv("GOOGLE_TOKEN")

print(f"TELEGRAM_TOKEN present: {bool(TELEGRAM_TOKEN)}")
print(f"GOOGLE_TOKEN present: {bool(GOOGLE_TOKEN)}")
print(f"GOOGLE_TOKEN length: {len(GOOGLE_TOKEN) if GOOGLE_TOKEN else 0}")

client = Anthropic(api_key=ANTHROPIC_API_KEY)

def get_calendar_service():
    try:
        token_bytes = base64.b64decode(GOOGLE_TOKEN.strip())
        creds = pickle.loads(token_bytes)
        print(f"Creds valid: {creds.valid}, expired: {creds.expired}")
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        print(f"Calendar error: {e}")
        return None

def get_events_today():
    service = get_calendar_service()
    if not service:
        return None
    now = datetime.datetime.now(datetime.timezone.utc)
    start = datetime.datetime(now.year, now.month, now.day, tzinfo=datetime.timezone.utc).isoformat()
    end = datetime.datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=datetime.timezone.utc).isoformat()
    events_result = service.events().list(calendarId='primary', timeMin=start, timeMax=end, singleEvents=True, orderBy='startTime').execute()
    return events_result.get('items', [])

def get_events_week():
    service = get_calendar_service()
    if not service:
        return None
    now = datetime.datetime.now(datetime.timezone.utc)
    start = now.isoformat()
    end = (now + datetime.timedelta(days=7)).isoformat()
    events_result = service.events().list(calendarId='primary', timeMin=start, timeMax=end, singleEvents=True, orderBy='startTime').execute()
    return events_result.get('items', [])

conversation_history = {}

SYSTEM_PROMPT = """Ты — личный помощник с доступом к Google Calendar пользователя.
Когда тебе передают данные календаря в скобках [Данные календаря: ...], используй их для ответа.
Отвечай кратко и по делу. Общаешься на том языке на котором пишет пользователь."""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я твой личный ассистент с доступом к календарю 🗓")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conversation_history[user_id] = []
    await update.message.reply_text("История очищена! 🔄")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text.lower()

    if user_id not in conversation_history:
        conversation_history[user_id] = []

    calendar_context = ""
    try:
        if any(word in user_text for word in ['сегодня', 'today', 'היום']):
            events = get_events_today()
            if events is None:
                calendar_context = "Ошибка подключения к календарю."
            elif events:
                calendar_context = "События сегодня: " + ", ".join([e['summary'] + " в " + e['start'].get('dateTime', e['start'].get('date', ''))[:16] for e in events])
            else:
                calendar_context = "Сегодня событий нет."
        elif any(word in user_text for word in ['неделя', 'week', 'שבוע']):
            events = get_events_week()
            if events is None:
                calendar_context = "Ошибка подключения к календарю."
            elif events:
                calendar_context = "События на неделю: " + ", ".join([e['summary'] + " " + e['start'].get('dateTime', e['start'].get('date', ''))[:16] for e in events])
            else:
                calendar_context = "На этой неделе событий нет."
    except Exception as e:
        calendar_context = f"Ошибка календаря: {str(e)}"

    message_content = user_text
    if calendar_context:
        message_content = f"{user_text}\n\n[Данные календаря: {calendar_context}]"

    conversation_history[user_id].append({"role": "user", "content": message_content})

    if len(conversation_history[user_id]) > 20:
        conversation_history[user_id] = conversation_history[user_id][-20:]

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=conversation_history[user_id]
        )
        assistant_reply = response.content[0].text
        conversation_history[user_id].append({"role": "assistant", "content": assistant_reply})
        await update.message.reply_text(assistant_reply)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен! Напиши ему в Telegram 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()
