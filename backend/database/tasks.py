from database.db import get_connection


def create_task(title, description="", priority="medium", due_date=None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO tasks (title, description, priority, due_date)
        VALUES (?, ?, ?, ?)
    """, (title, description, priority, due_date))

    task_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return task_id


def get_all_tasks():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tasks ORDER BY id DESC")

    tasks = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return tasks


def update_task(task_id, title, description, priority, due_date):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tasks
        SET title = ?, description = ?, priority = ?, due_date = ?
        WHERE id = ?
    """, (title, description, priority, due_date, task_id))

    updated = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return updated


def complete_task(task_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tasks
        SET status = 'completed'
        WHERE id = ?
    """, (task_id,))

    updated = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return updated


def delete_task(task_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM tasks WHERE id = ?",
        (task_id,)
    )

    deleted = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return deleted