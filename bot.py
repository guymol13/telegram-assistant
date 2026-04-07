import os
import json
import datetime
import base64
import pickle
import tempfile
from anthropic import Anthropic
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = base64.b64decode("c2stcHJvai1FS19hT1BWeUk5NkdVYmJXUUN1XzVqOHQteUFKbjhaQl9URi1QaF9tRTFlVUh2bnNBcVNRaGtOMzZQbmZxRGx6QWEzSXVvMXZnU1QzQmxia0ZKVVFYX2xhSEN6WHh6aUNxSTV4ZjVERllrWlBNNDQ5OEpTUnJsajllV1cyRm93QUJ6Tm9wbFItYXBZUGY3SlpEUVktRWltQlV2SUE=").decode()
GOOGLE_TOKEN = "gAWV9gMAAAAAAACMGWdvb2dsZS5vYXV0aDIuY3JlZGVudGlhbHOUjAtDcmVkZW50aWFsc5STlCmBlH2UKIwFdG9rZW6UjP15YTI5LmEwQWE3TVlpb1lDVVFPX2dkQUdycmJUcEhCNXgxRjZrNmstM21qWEo0akFhTWt5OVZGNklMRzFXY2NrTFJ3bHpPSkFrcC1UM2dIbWNZdmk3UmM5dEpiT0x6b29xVlpwaDk0WmhkMTdoMkJfeWlZaHRVdEZsTzcxR2t5QzdVTHBTNHBPSFh2QzY2RElxTG92RGtJUDNidHdZQ2hyZF80N1lCQVhDMGhEcnUzNml2UDlnT0I3dU43dnlEM0R3QkdHUjVpT2RpNFlBQWFDZ1lLQWJVU0FSTVNGUUhHWDJNaTFhbjZuYkJGTlE2dHFIZnBCbG1zQlEwMjA2lIwGZXhwaXJ5lIwIZGF0ZXRpbWWUjAhkYXRldGltZZSTlEMKB+oEBw4OMgAAAJSFlFKUjBFfcXVvdGFfcHJvamVjdF9pZJROjA9fdHJ1c3RfYm91bmRhcnmUTowQX3VuaXZlcnNlX2RvbWFpbpSMDmdvb2dsZWFwaXMuY29tlIwZX3VzZV9ub25fYmxvY2tpbmdfcmVmcmVzaJSJjAdfc2NvcGVzlF2UjChodHRwczovL3d3dy5nb29nbGVhcGlzLmNvbS9hdXRoL2NhbGVuZGFylGGMD19kZWZhdWx0X3Njb3Blc5ROjA5fcmVmcmVzaF90b2tlbpSMZjEvLzAzeXFwVGhRSXFWLWJDZ1lJQVJBQUdBTVNOZ0YtTDlJcjRzelNWbHlLbkhaTUJzT1N0TVQ5elRuMWhISG5KLWVPbzRLRjNHcEdfYzJYcldrczZYS1lNa01qbWtaVDN1TVpHZ5SMCV9pZF90b2tlbpROjA9fZ3JhbnRlZF9zY29wZXOUXZSMKGh0dHBzOi8vd3d3Lmdvb2dsZWFwaXMuY29tL2F1dGgvY2FsZW5kYXKUYYwKX3Rva2VuX3VyaZSMI2h0dHBzOi8vb2F1dGgyLmdvb2dsZWFwaXMuY29tL3Rva2VulIwKX2NsaWVudF9pZJSMSDQ1Mzk1NjYxODI2Ny1uM2I2MjlyNGZ1ZXJjZDBuaHZ1ZzZzaGl1Y2w4OGtubS5hcHBzLmdvb2dsZXVzZXJjb250ZW50LmNvbZSMDl9jbGllbnRfc2VjcmV0lIwjR09DU1BYLVJ5czhWWWxFdi1lVERpTVF4bDItM2NLdk93RGWUjAtfcmFwdF90b2tlbpROjBZfZW5hYmxlX3JlYXV0aF9yZWZyZXNolImMCF9hY2NvdW50lIwAlIwPX2NyZWRfZmlsZV9wYXRolE51Yi4="

client = Anthropic(api_key=ANTHROPIC_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def get_calendar_service():
    try:
        token_bytes = base64.b64decode(GOOGLE_TOKEN.strip())
        creds = pickle.loads(token_bytes)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return build("calendar", "v3", credentials=creds)
    except Exception as e:
        print(f"Calendar error: {e}")
        return None

def get_events_range(days=30):
    service = get_calendar_service()
    if not service:
        return None
    now = datetime.datetime.now(datetime.timezone.utc)
    start = now.isoformat()
    end = (now + datetime.timedelta(days=days)).isoformat()
    events_result = service.events().list(calendarId="primary", timeMin=start, timeMax=end, singleEvents=True, orderBy="startTime").execute()
    return events_result.get("items", [])

def get_events_today():
    service = get_calendar_service()
    if not service:
        return None
    now = datetime.datetime.now(datetime.timezone.utc)
    start = datetime.datetime(now.year, now.month, now.day, tzinfo=datetime.timezone.utc).isoformat()
    end = datetime.datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=datetime.timezone.utc).isoformat()
    events_result = service.events().list(calendarId="primary", timeMin=start, timeMax=end, singleEvents=True, orderBy="startTime").execute()
    return events_result.get("items", [])

def get_events_tomorrow():
    service = get_calendar_service()
    if not service:
        return None
    now = datetime.datetime.now(datetime.timezone.utc)
    tomorrow = now + datetime.timedelta(days=1)
    start = datetime.datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=datetime.timezone.utc).isoformat()
    end = datetime.datetime(tomorrow.year, tomorrow.month, tomorrow.day, 23, 59, 59, tzinfo=datetime.timezone.utc).isoformat()
    events_result = service.events().list(calendarId="primary", timeMin=start, timeMax=end, singleEvents=True, orderBy="startTime").execute()
    return events_result.get("items", [])

def get_events_week():
    service = get_calendar_service()
    if not service:
        return None
    now = datetime.datetime.now(datetime.timezone.utc)
    start = now.isoformat()
    end = (now + datetime.timedelta(days=7)).isoformat()
    events_result = service.events().list(calendarId="primary", timeMin=start, timeMax=end, singleEvents=True, orderBy="startTime").execute()
    return events_result.get("items", [])

def create_calendar_event(summary, start_datetime, end_datetime, description=None, location=None):
    service = get_calendar_service()
    if not service:
        return None
    event = {
        "summary": summary,
        "start": {"dateTime": start_datetime, "timeZone": "Europe/Moscow"},
        "end": {"dateTime": end_datetime, "timeZone": "Europe/Moscow"},
    }
    if description:
        event["description"] = description
    if location:
        event["location"] = location
    return service.events().insert(calendarId="primary", body=event).execute()

TOOLS = [
    {
        "name": "create_calendar_event",
        "description": "Создаёт новое событие в Google Calendar пользователя.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Название события"},
                "start_datetime": {"type": "string", "description": "Дата и время начала в формате ISO 8601, например 2026-04-07T15:00:00"},
                "end_datetime": {"type": "string", "description": "Дата и время окончания в формате ISO 8601, например 2026-04-07T16:00:00"},
                "description": {"type": "string", "description": "Описание события (необязательно)"},
                "location": {"type": "string", "description": "Место проведения (необязательно)"},
            },
            "required": ["summary", "start_datetime", "end_datetime"],
        },
    },
    {
        "name": "add_task",
        "description": "Добавляет новую задачу в список дел пользователя.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Текст задачи"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "get_tasks",
        "description": "Возвращает список задач пользователя.",
        "input_schema": {
            "type": "object",
            "properties": {
                "only_pending": {"type": "boolean", "description": "Если true — только невыполненные задачи. По умолчанию false."},
            },
            "required": [],
        },
    },
    {
        "name": "complete_task",
        "description": "Отмечает задачу как выполненную по её ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "ID задачи"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "set_reminder",
        "description": "Устанавливает напоминание, которое бот отправит пользователю в указанное время.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Текст напоминания"},
                "remind_at": {"type": "string", "description": "Дата и время напоминания в формате ISO 8601, например 2026-04-08T10:00:00"},
            },
            "required": ["text", "remind_at"],
        },
    },
]

TASKS_FILE = os.path.join(os.path.dirname(__file__), "tasks.json")
REMINDERS_FILE = os.path.join(os.path.dirname(__file__), "reminders.json")
MSK = datetime.timezone(datetime.timedelta(hours=3))

def load_tasks() -> list:
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_tasks(tasks: list):
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

def add_task(text: str) -> dict:
    tasks = load_tasks()
    new_id = max((t["id"] for t in tasks), default=0) + 1
    task = {"id": new_id, "text": text, "done": False, "created_at": datetime.datetime.now().isoformat()}
    tasks.append(task)
    save_tasks(tasks)
    return task

def get_tasks(only_pending: bool = False) -> list:
    tasks = load_tasks()
    return [t for t in tasks if not t["done"]] if only_pending else tasks

def complete_task(task_id: int) -> dict | None:
    tasks = load_tasks()
    for task in tasks:
        if task["id"] == task_id:
            task["done"] = True
            save_tasks(tasks)
            return task
    return None


def load_reminders() -> list:
    if os.path.exists(REMINDERS_FILE):
        with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_reminders(reminders: list):
    with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(reminders, f, ensure_ascii=False, indent=2)

def add_reminder(user_id: int, text: str, remind_at: str) -> dict:
    reminders = load_reminders()
    new_id = max((r["id"] for r in reminders), default=0) + 1
    reminder = {
        "id": new_id,
        "user_id": user_id,
        "text": text,
        "remind_at": remind_at,
        "sent": False,
        "created_at": datetime.datetime.now(MSK).isoformat(),
    }
    reminders.append(reminder)
    save_reminders(reminders)
    return reminder

async def check_reminders(context):
    now = datetime.datetime.now(MSK)
    reminders = load_reminders()
    changed = False
    for reminder in reminders:
        if reminder["sent"]:
            continue
        remind_at = datetime.datetime.fromisoformat(reminder["remind_at"])
        if remind_at.tzinfo is None:
            remind_at = remind_at.replace(tzinfo=MSK)
        if now >= remind_at:
            try:
                await context.bot.send_message(
                    chat_id=reminder["user_id"],
                    text=f"⏰ Напоминание: {reminder['text']}",
                )
                reminder["sent"] = True
                changed = True
            except Exception as e:
                print(f"Reminder send error: {e}")
    if changed:
        save_reminders(reminders)


async def transcribe_voice(file) -> str:
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        await file.download_to_drive(tmp.name)
        tmp_path = tmp.name
    try:
        with open(tmp_path, "rb") as audio:
            result = openai_client.audio.transcriptions.create(model="whisper-1", file=audio)
        return result.text
    finally:
        os.remove(tmp_path)

conversation_history = {}

SYSTEM_PROMPT = """Ты — личный помощник с доступом к Google Calendar и списку задач пользователя.
Когда тебе передают данные календаря в скобках [Данные календаря: ...], используй их для ответа.
Когда пользователь просит создать, добавить или запланировать событие в календарь — используй инструмент create_calendar_event.
Когда пользователь просит добавить задачу, напомнить сделать что-то, создать напоминание — используй add_task.
Когда пользователь просит показать задачи или список дел — используй get_tasks.
Когда пользователь отмечает задачу выполненной или просит удалить/закрыть задачу — используй complete_task.
Когда пользователь просит напомнить что-либо в определённое время — используй set_reminder.
Часовой пояс пользователя: Europe/Moscow (UTC+3). Если пользователь не указал год, используй текущий.
Отвечай кратко и по делу. Общаешься на том языке на котором пишет пользователь."""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я твой личный ассистент с доступом к календарю!")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conversation_history[user_id] = []
    await update.message.reply_text("История очищена!")

async def process_text(user_id: int, user_text: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    calendar_context = ""
    try:
        events = get_events_range(30)
        if events is None:
            calendar_context = "Ошибка подключения к календарю."
        elif events:
            calendar_context = "Предстоящие события: " + "; ".join([
                e["summary"] + " — " + e["start"].get("dateTime", e["start"].get("date", ""))[:16]
                for e in events
            ])
        else:
            calendar_context = "Ближайшие 30 дней событий нет."
    except Exception as e:
        calendar_context = f"Ошибка календаря: {str(e)}"

    import datetime as dt
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).strftime("%d %B %Y")
    message_content = f"{user_text}\n\n[Сегодня: {today}. Данные календаря: {calendar_context}]"

    conversation_history[user_id].append({"role": "user", "content": message_content})

    if len(conversation_history[user_id]) > 20:
        conversation_history[user_id] = conversation_history[user_id][-20:]

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=conversation_history[user_id],
    )

    if response.stop_reason == "tool_use":
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            args = block.input
            try:
                if block.name == "create_calendar_event":
                    event = create_calendar_event(
                        summary=args["summary"],
                        start_datetime=args["start_datetime"],
                        end_datetime=args["end_datetime"],
                        description=args.get("description"),
                        location=args.get("location"),
                    )
                    tool_result_content = f"Событие создано: {event.get('htmlLink', 'OK')}"
                elif block.name == "add_task":
                    task = add_task(args["text"])
                    tool_result_content = f"Задача добавлена с ID {task['id']}: {task['text']}"
                elif block.name == "get_tasks":
                    tasks = get_tasks(only_pending=args.get("only_pending", False))
                    if not tasks:
                        tool_result_content = "Задач нет."
                    else:
                        lines = [f"{'✅' if t['done'] else '☐'} [{t['id']}] {t['text']}" for t in tasks]
                        tool_result_content = "\n".join(lines)
                elif block.name == "complete_task":
                    task = complete_task(args["task_id"])
                    tool_result_content = f"Задача выполнена: {task['text']}" if task else f"Задача с ID {args['task_id']} не найдена."
                elif block.name == "set_reminder":
                    reminder = add_reminder(user_id, args["text"], args["remind_at"])
                    tool_result_content = f"Напоминание установлено на {args['remind_at']}: {args['text']}"
                else:
                    tool_result_content = "Неизвестный инструмент."
            except Exception as e:
                tool_result_content = f"Ошибка: {str(e)}"
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": tool_result_content,
            })

        conversation_history[user_id].append({"role": "assistant", "content": response.content})
        conversation_history[user_id].append({"role": "user", "content": tool_results})

        final_response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=conversation_history[user_id],
        )
        assistant_reply = final_response.content[0].text
        conversation_history[user_id].append({"role": "assistant", "content": assistant_reply})
    else:
        assistant_reply = response.content[0].text
        conversation_history[user_id].append({"role": "assistant", "content": assistant_reply})

    return assistant_reply


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        reply = await process_text(update.effective_user.id, update.message.text, update, context)
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)}")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        voice_file = await update.message.voice.get_file()
        user_text = await transcribe_voice(voice_file)
        if not user_text.strip():
            await update.message.reply_text("Не удалось распознать голосовое сообщение.")
            return
        await update.message.reply_text(f"_{user_text}_", parse_mode="Markdown")
        reply = await process_text(update.effective_user.id, user_text, update, context)
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.job_queue.run_repeating(check_reminders, interval=60, first=10)
    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
