import os
import time

import pymysql
from pymysql.cursors import DictCursor
from flask import Flask, redirect, render_template_string, request, url_for

# Configurazione tramite variabili d'ambiente (le imposta il docker-compose)
PORT = int(os.getenv("PORT", "5050"))
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "app")
DB_PASSWORD = os.getenv("DB_PASSWORD", "app")
DB_NAME = os.getenv("DB_NAME", "todos")

app = Flask(__name__)

PAGE = """
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Todo</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 480px; margin: 3rem auto; padding: 0 1rem; }
    form.add { display: flex; gap: .5rem; margin-bottom: 1.5rem; }
    form.add input { flex: 1; padding: .5rem; }
    ul { list-style: none; padding: 0; }
    li { display: flex; align-items: center; gap: .5rem; padding: .5rem 0; border-bottom: 1px solid #ddd; }
    li span { flex: 1; }
    li.done span { text-decoration: line-through; color: #888; }
    button { cursor: pointer; }
  </style>
</head>
<body>
  <h1>Lista cose da fare</h1>
  <form class="add" method="post" action="{{ url_for('add') }}">
    <input name="title" placeholder="Nuova attività" required autofocus>
    <button>Aggiungi</button>
  </form>
  <ul>
    {% for t in todos %}
    <li class="{{ 'done' if t['done'] else '' }}">
      <form method="post" action="{{ url_for('toggle', todo_id=t['id']) }}">
        <button>{{ '↩' if t['done'] else '✓' }}</button>
      </form>
      <span>{{ t['title'] }}</span>
      <form method="post" action="{{ url_for('delete', todo_id=t['id']) }}">
        <button>✕</button>
      </form>
    </li>
    {% else %}
    <li>Nessuna attività.</li>
    {% endfor %}
  </ul>
</body>
</html>
"""


def get_db():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=DictCursor,
        autocommit=True,
    )


def query(sql, params=(), fetch=False):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall() if fetch else None
    finally:
        conn.close()


def init_db():
    # Riprova per un po': il DB potrebbe non essere ancora pronto
    for attempt in range(30):
        try:
            query(
                """CREATE TABLE IF NOT EXISTS todos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    done TINYINT(1) NOT NULL DEFAULT 0
                )"""
            )
            return
        except pymysql.MySQLError as e:
            print(f"DB non pronto ({attempt + 1}/30): {e}", flush=True)
            time.sleep(2)
    raise RuntimeError("Impossibile connettersi al database")


@app.get("/")
def index():
    todos = query("SELECT * FROM todos ORDER BY id DESC", fetch=True)
    return render_template_string(PAGE, todos=todos)


@app.post("/add")
def add():
    title = request.form.get("title", "").strip()
    if title:
        query("INSERT INTO todos (title) VALUES (%s)", (title,))
    return redirect(url_for("index"))


@app.post("/toggle/<int:todo_id>")
def toggle(todo_id):
    query("UPDATE todos SET done = 1 - done WHERE id = %s", (todo_id,))
    return redirect(url_for("index"))


@app.post("/delete/<int:todo_id>")
def delete(todo_id):
    query("DELETE FROM todos WHERE id = %s", (todo_id,))
    return redirect(url_for("index"))


@app.get("/health")
def health():
    query("SELECT 1")
    return {"status": "ok"}


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)