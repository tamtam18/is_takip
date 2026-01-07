from flask import Flask, request, redirect, render_template_string
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB = "tasks.db"

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

# TABLO
with db() as con:
    con.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        start_dt TEXT,
        end_dt TEXT,
        done INTEGER DEFAULT 0,
        archived INTEGER DEFAULT 0
    )
    """)

@app.route("/", methods=["GET", "POST"])
def index():
    con = db()

    # ---- EKLE (BOŞ KAYIT ENGELİ) ----
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if title:  # boşsa ekleme
            con.execute(
                "INSERT INTO tasks (title, start_dt) VALUES (?,?)",
                (title.title(), datetime.now().isoformat())
            )
            con.commit()
        return redirect("/")

    # ---- FİLTRELER ----
    f = request.args.get("f", "active")
    start = request.args.get("start")
    end = request.args.get("end")

    where = "WHERE 1=1"
    params = []

    if f == "active":
        where += " AND archived=0"
    elif f == "open":
        where += " AND archived=0 AND done=0"
    elif f == "done":
        where += " AND archived=0 AND done=1"
    elif f == "archive":
        where += " AND archived=1"

    if start and end:
        where += " AND date(start_dt) BETWEEN ? AND ?"
        params.extend([start, end])

    rows = con.execute(
        f"SELECT * FROM tasks {where} ORDER BY id DESC",
        params
    ).fetchall()

    # ---- HESAPLAR ----
    now = datetime.now()
    tasks = []

    for r in rows:
        start_dt = datetime.fromisoformat(r["start_dt"])
        end_dt = datetime.fromisoformat(r["end_dt"]) if r["end_dt"] else now
        delta = end_dt - start_dt

        days = delta.days
        hours = delta.seconds // 3600

        if r["done"]:
            status = f"{days} gün {hours} saat sürdü"
        else:
            status = "Bugün" if days == 0 else f"{days} gün {hours} saat geçti"

        cls = ""
        if not r["done"]:
            if days >= 4:
                cls = "late"
            elif days >= 2:
                cls = "warn"

        tasks.append(dict(r, status=status, cls=cls))

    return render_template_string("""
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body { font-family:Arial; background:#f4f7ff; padding:20px }
h2 { text-align:center }
form { margin:10px auto; text-align:center }
input,button { padding:8px }
table { width:100%; border-collapse:collapse; margin-top:15px }
th,td { border:1px solid #ccc; padding:8px; text-align:center }
th { background:#ffd9b3 }
.done { background:#c8f7c5 }
.warn { background:#fff3b0 }
.late { background:#f7b0b0 }
.filters a { margin:5px; font-weight:bold; text-decoration:none }
</style>
</head>
<body>

<h2>İş Takip Sistemi</h2>

<form method="post">
<input name="title" placeholder="İş başlığı">
<button>Kaydet</button>
</form>

<div class="filters" style="text-align:center">
<a href="/?f=active">Aktif</a>
<a href="/?f=open">Devam</a>
<a href="/?f=done">Biten</a>
<a href="/?f=archive">Arşiv</a>
</div>

{% if request.args.get('f') == 'archive' %}
<form method="get">
<input type="hidden" name="f" value="archive">
Başlangıç: <input type="date" name="start">
Bitiş: <input type="date" name="end">
<button>Filtrele</button>
</form>
{% endif %}

<table>
<tr>
<th>✔</th>
<th>İş</th>
<th>Başlangıç</th>
<th>Bitiş</th>
<th>Süre</th>
<th>İşlem</th>
</tr>

{% for t in tasks %}
<tr class="{{t.cls}} {% if t.done %}done{% endif %}">
<td>
<form method="post" action="/toggle/{{t.id}}">
<input type="checkbox" onchange="this.form.submit()" {% if t.done %}checked{% endif %}>
</form>
</td>
<td>{{t.title}}</td>
<td>{{t.start_dt[:16].replace('T',' ')}}</td>
<td>{{t.end_dt[:16].replace('T',' ') if t.end_dt else ""}}</td>
<td>{{t.status}}</td>
<td>
{% if t.archived %}
<form method="post" action="/unarchive/{{t.id}}">
<button>📤 Çıkar</button>
</form>
{% elif t.done %}
<form method="post" action="/archive/{{t.id}}">
<button>📦 Arşiv</button>
</form>
{% else %}
—
{% endif %}
</td>
</tr>
{% endfor %}
</table>

</body>
</html>
""", tasks=tasks)

@app.route("/toggle/<int:id>", methods=["POST"])
def toggle(id):
    con = db()
    r = con.execute("SELECT done FROM tasks WHERE id=?", (id,)).fetchone()
    if r["done"] == 0:
        con.execute(
            "UPDATE tasks SET done=1, end_dt=? WHERE id=?",
            (datetime.now().isoformat(), id)
        )
    else:
        con.execute(
            "UPDATE tasks SET done=0, end_dt=NULL WHERE id=?",
            (id,)
        )
    con.commit()
    return redirect("/")

@app.route("/archive/<int:id>", methods=["POST"])
def archive(id):
    con = db()
    con.execute(
        "UPDATE tasks SET archived=1 WHERE id=? AND done=1",
        (id,)
    )
    con.commit()
    return redirect("/")

@app.route("/unarchive/<int:id>", methods=["POST"])
def unarchive(id):
    con = db()
    con.execute(
        "UPDATE tasks SET archived=0 WHERE id=?",
        (id,)
    )
    con.commit()
    return redirect("/?f=archive")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
