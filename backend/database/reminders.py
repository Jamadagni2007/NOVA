from database.db import get_connection
from datetime import datetime, timezone


def create_reminder(title, remind_at):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO reminders (title, remind_at)
        VALUES (?, ?)
    """, (title, remind_at))

    reminder_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return reminder_id


def get_all_reminders():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM reminders
        ORDER BY remind_at ASC
    """)

    reminders = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return reminders


def delete_reminder(reminder_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM reminders
        WHERE id = ?
    """, (reminder_id,))

    deleted = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return deleted


def get_due_reminders():
    conn = get_connection()
    cursor = conn.cursor()

    current_time = datetime.now(timezone.utc).isoformat()

    cursor.execute("""
        SELECT * FROM reminders
        WHERE status = 'pending'
        AND remind_at <= ?
    """, (current_time,))

    reminders = [dict(row) for row in cursor.fetchall()]

    for reminder in reminders:
        cursor.execute("""
            UPDATE reminders
            SET status = 'triggered'
            WHERE id = ?
        """, (reminder["id"],))

    conn.commit()
    conn.close()

    return reminders