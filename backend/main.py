import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo
from typing import Optional, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from winotify import Notification
except ImportError:
    Notification = None

# AI ENGINE
from ai_engine.model import ask_nova

# DATABASE
from database.db import (
    initialize_database,
    save_message,
    get_chat_history,
    save_memory,
    get_all_memories,
    delete_memory
)

# TASKS
from database.tasks import (
    create_task,
    get_all_tasks,
    update_task,
    complete_task,
    delete_task
)

# REMINDERS
from database.reminders import (
    create_reminder,
    get_all_reminders,
    delete_reminder,
    get_due_reminders
)


# TIMEZONE
IST = ZoneInfo("Asia/Kolkata")


# ==========================================
# REMINDER BACKGROUND SERVICE
# ==========================================

async def reminder_checker():
    # Show each due reminder once per backend run.
    notified = set()
    while True:
        try:
            due = await asyncio.to_thread(get_due_reminders)
            for reminder in due:
                key = str(reminder.get("id") or f"{reminder.get('title', '')}|{reminder.get('remind_at', '')}")
                if key in notified:
                    continue
                notified.add(key)
                title = str(reminder.get("title", "You have a reminder"))
                print("\\nNOVA REMINDER:", title)
                if Notification is not None:
                    try:
                        toast = Notification(
                            app_id="NOVA Personal AI",
                            title="NOVA Reminder",
                            msg=title,
                            duration="long"
                        )
                        await asyncio.to_thread(toast.show)
                    except Exception as toast_error:
                        print("Windows notification error:", toast_error)
                else:
                    print("Install winotify to enable Windows notifications.")
        except Exception as error:
            print("Reminder error:", error)
        await asyncio.sleep(10)


# ==========================================
# APPLICATION LIFESPAN
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    initialize_database()

    reminder_task = asyncio.create_task(
        reminder_checker()
    )

    print("NOVA AI Assistant Started Successfully!")

    yield

    reminder_task.cancel()

    try:
        await reminder_task
    except asyncio.CancelledError:
        pass

    print("NOVA AI Assistant Stopped.")


# ==========================================
# FASTAPI APPLICATION
# ==========================================

app = FastAPI(
    title="NOVA AI Assistant",
    description="Your Personal AI Assistant",
    version="6.0",
    lifespan=lifespan
)


# ==========================================
# CORS CONFIGURATION
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ==========================================
# REQUEST MODELS
# ==========================================

class ChatRequest(BaseModel):

    message: str

    session_id: str = Field(
        default_factory=lambda: str(uuid4())
    )


class TaskRequest(BaseModel):

    title: str

    description: str = ""

    priority: Literal[
        "low",
        "medium",
        "high"
    ] = "medium"

    due_date: Optional[str] = None


class TaskUpdate(BaseModel):

    title: str

    description: str = ""

    priority: Literal[
        "low",
        "medium",
        "high"
    ] = "medium"

    due_date: Optional[str] = None


class ReminderRequest(BaseModel):

    title: str

    remind_at: datetime


class MemoryRequest(BaseModel):

    content: str




@app.post("/notifications/test")
def test_notification():
    if Notification is None:
        raise HTTPException(status_code=503, detail="Install winotify to enable Windows notifications.")
    try:
        Notification(
            app_id="NOVA Personal AI",
            title="NOVA",
            msg="Windows notifications are working!",
            duration="short"
        ).show()
        return {"success": True, "message": "Test notification sent"}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))

# ==========================================
# HOME ROUTE
# ==========================================

@app.get("/")
def home():

    return {
        "assistant": "NOVA",
        "message": "Welcome to NOVA AI Assistant",
        "status": "Online",
        "version": "6.0"
    }


# ==========================================
# CHAT ROUTES
# ==========================================
@app.post("/chat")
def chat(request: ChatRequest):

    message = request.message.strip()
    lower_message = message.lower()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )

    # ==================================
    # AUTOMATIC MEMORY SAVING
    # ==================================

    memory_triggers = [
        "remember that ",
        "remember ",
        "don't forget that ",
        "dont forget that "
    ]

    for trigger in memory_triggers:

        if lower_message.startswith(trigger):

            memory_content = message[len(trigger):].strip()

            if memory_content:

                save_memory(memory_content)

                response = (
                    "I've saved that in my long-term memory. "
                    "I'll remember it for future conversations."
                )

                save_message(
                    request.session_id,
                    "user",
                    message
                )

                save_message(
                    request.session_id,
                    "assistant",
                    response
                )

                return {
                    "assistant": "NOVA",
                    "response": response,
                    "session_id": request.session_id
                }

    # ==================================
    # RECALL SAVED MEMORIES
    # ==================================

    recall_triggers = [
        "what do you remember",
        "what have you remembered",
        "show my memories",
        "what do you know about me"
    ]

    if any(
        trigger in lower_message
        for trigger in recall_triggers
    ):

        memories = get_all_memories()

        if memories:
            response = "Here is what I remember about you:\n\n"

            response += "\n".join(
                f"- {memory}" for memory in memories
            )
        else:
            response = "I haven't saved any memories yet."

        save_message(
            request.session_id,
            "user",
            message
        )

        save_message(
            request.session_id,
            "assistant",
            response
        )

        return {
            "assistant": "NOVA",
            "response": response,
            "session_id": request.session_id
        }

    # ==================================
    # NORMAL AI CONVERSATION
    # ==================================

    try:

        history = get_chat_history(
            request.session_id
        )

        response = ask_nova(
            message,
            history
        )

        save_message(
            request.session_id,
            "user",
            message
        )

        save_message(
            request.session_id,
            "assistant",
            response
        )

        return {
            "assistant": "NOVA",
            "response": response,
            "session_id": request.session_id
        }

    except Exception as error:

        print("AI Engine Error:", error)

        raise HTTPException(
            status_code=500,
            detail="NOVA AI engine encountered an error."
        )

@app.get("/history/{session_id}")
def chat_history(session_id: str):

    history = get_chat_history(session_id)

    return {
        "session_id": session_id,
        "history": history
    }


# ==========================================
# TASK MANAGEMENT
# ==========================================

@app.post("/tasks")
def add_task(request: TaskRequest):

    if not request.title.strip():
        raise HTTPException(
            status_code=400,
            detail="Task title cannot be empty"
        )

    task_id = create_task(
        request.title,
        request.description,
        request.priority,
        request.due_date
    )

    return {
        "success": True,
        "message": "Task created successfully",
        "task_id": task_id
    }


@app.get("/tasks")
def list_tasks():

    return {
        "tasks": get_all_tasks()
    }


@app.put("/tasks/{task_id}")
def edit_task(
    task_id: int,
    request: TaskUpdate
):

    updated = update_task(
        task_id,
        request.title,
        request.description,
        request.priority,
        request.due_date
    )

    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    return {
        "success": True,
        "message": "Task updated successfully"
    }


@app.put("/tasks/{task_id}/complete")
def finish_task(task_id: int):

    completed = complete_task(task_id)

    if not completed:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    return {
        "success": True,
        "message": "Task completed successfully"
    }


@app.delete("/tasks/{task_id}")
def remove_task(task_id: int):

    deleted = delete_task(task_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    return {
        "success": True,
        "message": "Task deleted successfully"
    }


# ==========================================
# REMINDER MANAGEMENT
# ==========================================

@app.post("/reminders")
def add_reminder(request: ReminderRequest):

    remind_at = request.remind_at

    if remind_at.tzinfo is None:
        remind_at = remind_at.replace(
            tzinfo=IST
        )

    remind_at = remind_at.astimezone(
        timezone.utc
    )

    if remind_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Reminder time must be in the future"
        )

    reminder_id = create_reminder(
        request.title,
        remind_at.isoformat()
    )

    return {
        "success": True,
        "message": "Reminder created successfully",
        "reminder_id": reminder_id
    }


@app.get("/reminders")
def list_reminders():

    return {
        "reminders": get_all_reminders()
    }


@app.delete("/reminders/{reminder_id}")
def remove_reminder(reminder_id: int):

    deleted = delete_reminder(reminder_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Reminder not found"
        )

    return {
        "success": True,
        "message": "Reminder deleted successfully"
    }


# ==========================================
# DAILY PLANNER
# ==========================================

@app.get("/planner/today")
def today_planner():

    today = datetime.now(IST).date()

    return get_planner_data(today)


@app.get("/planner/{plan_date}")
def daily_planner(plan_date: date):

    return get_planner_data(plan_date)


def get_planner_data(plan_date):

    all_tasks = get_all_tasks()

    daily_tasks = [
        task for task in all_tasks
        if task["due_date"] == plan_date.isoformat()
    ]

    pending_tasks = [
        task for task in daily_tasks
        if task["status"] == "pending"
    ]

    completed_tasks = [
        task for task in daily_tasks
        if task["status"] == "completed"
    ]

    all_reminders = get_all_reminders()

    daily_reminders = []

    for reminder in all_reminders:

        reminder_time = datetime.fromisoformat(
            reminder["remind_at"]
        )

        if reminder_time.tzinfo is None:
            reminder_time = reminder_time.replace(
                tzinfo=timezone.utc
            )

        reminder_date = reminder_time.astimezone(
            IST
        ).date()

        if reminder_date == plan_date:
            daily_reminders.append(reminder)

    return {
        "date": plan_date.isoformat(),
        "total_tasks": len(daily_tasks),
        "pending_tasks": pending_tasks,
        "completed_tasks": completed_tasks,
        "reminders": daily_reminders
    }


# ==========================================
# LONG-TERM MEMORY
# ==========================================

@app.post("/memories")
def add_memory(request: MemoryRequest):

    content = request.content.strip()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Memory cannot be empty"
        )

    save_memory(content)

    return {
        "success": True,
        "message": "Memory saved successfully",
        "memory": content
    }


@app.get("/memories")
def list_memories():

    return {
        "memories": get_all_memories()
    }


@app.delete("/memories/{memory_id}")
def remove_memory(memory_id: int):

    deleted = delete_memory(memory_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Memory not found"
        )

    return {
        "success": True,
        "message": "Memory deleted successfully"
    }


# ==========================================
# END OF NOVA BACKEND
# ==========================================