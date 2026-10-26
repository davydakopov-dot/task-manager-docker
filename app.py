
import os
import logging
from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "taskdb"),
        user=os.getenv("DB_USER", "taskuser"),
        password=os.getenv("DB_PASSWORD", "taskpass")
    )

def init_db():
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    completed BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
        connection.commit()
        logger.info("Database initialized")
    finally:
        connection.close()

@app.get("/")
def home():
    return jsonify({
        "application": "Task Manager API",
        "status": "running",
        "endpoints": [
            "GET /health",
            "GET /tasks",
            "POST /tasks",
            "PATCH /tasks/<id>",
            "DELETE /tasks/<id>"
        ]
    })

@app.get("/health")
def health():
    try:
        connection = get_connection()
        connection.close()
        return jsonify({"status": "ok", "database": "connected"})
    except Exception:
        logger.exception("Health check failed")
        return jsonify({"status": "error", "database": "unavailable"}), 503

@app.get("/tasks")
def get_tasks():
    connection = get_connection()
    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, title, completed, created_at
                FROM tasks ORDER BY id
            """)
            tasks = cursor.fetchall()
        return jsonify([dict(task) for task in tasks])
    finally:
        connection.close()

@app.post("/tasks")
def create_task():
    data = request.get_json(silent=True) or {}
    title = data.get("title")

    if not isinstance(title, str) or not title.strip():
        return jsonify({"error": "A non-empty title is required"}), 400

    connection = get_connection()
    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                INSERT INTO tasks (title)
                VALUES (%s)
                RETURNING id, title, completed, created_at
            """, (title.strip(),))
            task = dict(cursor.fetchone())
        connection.commit()
        logger.info("Created task id=%s", task["id"])
        return jsonify(task), 201
    finally:
        connection.close()

@app.patch("/tasks/<int:task_id>")
def update_task(task_id):
    data = request.get_json(silent=True) or {}
    if not isinstance(data.get("completed"), bool):
        return jsonify({"error": "completed must be true or false"}), 400

    connection = get_connection()
    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                UPDATE tasks SET completed = %s
                WHERE id = %s
                RETURNING id, title, completed, created_at
            """, (data["completed"], task_id))
            task = cursor.fetchone()
        connection.commit()

        if task is None:
            return jsonify({"error": "Task not found"}), 404
        return jsonify(dict(task))
    finally:
        connection.close()

@app.delete("/tasks/<int:task_id>")
def delete_task(task_id):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
            deleted = cursor.rowcount
        connection.commit()

        if not deleted:
            return jsonify({"error": "Task not found"}), 404
        logger.info("Deleted task id=%s", task_id)
        return jsonify({"message": "Task deleted"})
    finally:
        connection.close()

if __name__ == "__main__":
    import time

    for attempt in range(15):
        try:
            init_db()
            break
        except psycopg2.OperationalError:
            logger.warning("Database not ready, attempt %s/15", attempt + 1)
            time.sleep(2)
    else:
        raise RuntimeError("Could not connect to the database")

    app.run(host="0.0.0.0", port=5000)
