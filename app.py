from flask import (Flask, render_template, request,
                   jsonify, session, redirect, url_for, Response)
import sqlite3, json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "gate_ga_2026"

DB    = "gate_ga.db"
USERS = ["arko", "devynashi"]

COLORS = {
    "Quantitative": {"accent":"#4F46E5", "bg":"#EEF2FF", "emoji":"🔢"},
    "Verbal":       {"accent":"#059669", "bg":"#ECFDF5", "emoji":"📝"},
    "Spatial":      {"accent":"#7C3AED", "bg":"#F5F3FF", "emoji":"🔷"},
    "Analytical":   {"accent":"#EA580C", "bg":"#FFF7ED", "emoji":"🧠"},
}

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def get_user():
    return session.get("user")

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/login/<u>")
def login(u):
    if u in USERS:
        session["user"] = u
    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))

@app.route("/dashboard")
def dashboard():
    u = get_user()
    if not u: return redirect(url_for("home"))
    conn = db()
    cats = []
    for cat, col in COLORS.items():
        total = conn.execute(
            "SELECT COUNT(*) FROM questions WHERE category=?", (cat,)
        ).fetchone()[0]
        if total == 0: continue
        solved = conn.execute(
            "SELECT COUNT(*) FROM progress "
            "WHERE user=? AND solved=1 "
            "AND question_id IN (SELECT id FROM questions WHERE category=?)",
            (u, cat)
        ).fetchone()[0]
        rev = conn.execute(
            "SELECT COUNT(*) FROM progress "
            "WHERE user=? AND revision=1 "
            "AND question_id IN (SELECT id FROM questions WHERE category=?)",
            (u, cat)
        ).fetchone()[0]
        cats.append({
            "name": cat, "total": total,
            "solved": solved, "revision": rev,
            "pct": round(solved / total * 100) if total else 0,
            "colors": col
        })
    conn.close()
    return render_template("dashboard.html", categories=cats)

@app.route("/subject/<cat>")
def subject(cat):
    u = get_user()
    if not u: return redirect(url_for("home"))
    conn = db()
    topic_rows = conn.execute(
        "SELECT DISTINCT topic FROM questions WHERE category=? ORDER BY topic", (cat,)
    ).fetchall()
    topics = []
    for r in topic_rows:
        t = r["topic"]
        total = conn.execute(
            "SELECT COUNT(*) FROM questions WHERE category=? AND topic=?", (cat, t)
        ).fetchone()[0]
        solved = conn.execute(
            "SELECT COUNT(*) FROM progress "
            "WHERE user=? AND solved=1 "
            "AND question_id IN (SELECT id FROM questions WHERE category=? AND topic=?)",
            (u, cat, t)
        ).fetchone()[0]
        rev = conn.execute(
            "SELECT COUNT(*) FROM progress "
            "WHERE user=? AND revision=1 "
            "AND question_id IN (SELECT id FROM questions WHERE category=? AND topic=?)",
            (u, cat, t)
        ).fetchone()[0]
        topics.append({
            "name": t, "total": total, "solved": solved, "revision": rev,
            "pct": round(solved / total * 100) if total else 0
        })
    conn.close()
    return render_template("subject.html", category=cat,
                           topics=topics, colors=COLORS.get(cat, {}))

@app.route("/topic/<cat>/<path:topic>")
def topic(cat, topic):
    u = get_user()
    if not u: return redirect(url_for("home"))
    conn = db()
    rows = conn.execute(
        "SELECT * FROM questions WHERE category=? AND topic=? ORDER BY CAST(id AS INTEGER)",
        (cat, topic)
    ).fetchall()
    questions = []
    for q in rows:
        p = conn.execute(
            "SELECT solved, revision FROM progress WHERE user=? AND question_id=?",
            (u, q["id"])
        ).fetchone()
        questions.append({
            "id": q["id"], "title": q["title"], "url": q["url"],
            "solved":   p["solved"]   if p else 0,
            "revision": p["revision"] if p else 0,
        })
    conn.close()
    return render_template("topic.html", category=cat, topic=topic,
                           questions=questions, colors=COLORS.get(cat, {}))

@app.route("/toggle", methods=["POST"])
def toggle():
    u = get_user()
    if not u: return jsonify({"error": "not logged in"}), 401
    data  = request.json
    qid   = data.get("qid")
    field = data.get("field")
    val   = int(data.get("value", 0))
    if field not in ("solved", "revision"):
        return jsonify({"error": "bad field"}), 400
    conn = db()
    exists = conn.execute(
        "SELECT 1 FROM progress WHERE user=? AND question_id=?", (u, qid)
    ).fetchone()
    if exists:
        conn.execute(
            f"UPDATE progress SET {field}=? WHERE user=? AND question_id=?",
            (val, u, qid)
        )
    else:
        s = val if field == "solved"   else 0
        r = val if field == "revision" else 0
        conn.execute(
            "INSERT INTO progress (user, question_id, solved, revision) VALUES (?,?,?,?)",
            (u, qid, s, r)
        )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/revision")
def revision():
    u = get_user()
    if not u: return redirect(url_for("home"))
    conn = db()
    cats = []
    for cat, col in COLORS.items():
        cnt = conn.execute(
            "SELECT COUNT(*) FROM progress p "
            "JOIN questions q ON p.question_id=q.id "
            "WHERE p.user=? AND p.revision=1 AND q.category=?", (u, cat)
        ).fetchone()[0]
        if cnt > 0:
            cats.append({"name": cat, "count": cnt, "colors": col})
    conn.close()
    return render_template("revision.html", categories=cats)

@app.route("/revision/<cat>")
def revision_subject(cat):
    u = get_user()
    if not u: return redirect(url_for("home"))
    conn = db()
    rows = conn.execute(
        "SELECT DISTINCT q.topic FROM progress p "
        "JOIN questions q ON p.question_id=q.id "
        "WHERE p.user=? AND p.revision=1 AND q.category=? ORDER BY q.topic",
        (u, cat)
    ).fetchall()
    topics = []
    for r in rows:
        t = r["topic"]
        cnt = conn.execute(
            "SELECT COUNT(*) FROM progress p "
            "JOIN questions q ON p.question_id=q.id "
            "WHERE p.user=? AND p.revision=1 AND q.category=? AND q.topic=?",
            (u, cat, t)
        ).fetchone()[0]
        topics.append({"name": t, "count": cnt})
    conn.close()
    return render_template("rev_subject.html", category=cat,
                           topics=topics, colors=COLORS.get(cat, {}))

@app.route("/revision/<cat>/<path:topic>")
def revision_topic(cat, topic):
    u = get_user()
    if not u: return redirect(url_for("home"))
    conn = db()
    rows = conn.execute(
        "SELECT q.*, p.solved, p.revision FROM questions q "
        "JOIN progress p ON q.id=p.question_id "
        "WHERE p.user=? AND p.revision=1 AND q.category=? AND q.topic=? "
        "ORDER BY CAST(q.id AS INTEGER)",
        (u, cat, topic)
    ).fetchall()
    questions = [{"id": q["id"], "title": q["title"], "url": q["url"],
                  "solved": q["solved"], "revision": q["revision"]} for q in rows]
    conn.close()
    return render_template("rev_topic.html", category=cat, topic=topic,
                           questions=questions, colors=COLORS.get(cat, {}))

@app.route("/backup/download")
def backup_download():
    u = get_user()
    if not u: return redirect(url_for("home"))
    conn = db()
    rows = conn.execute("SELECT * FROM progress WHERE user=?", (u,)).fetchall()
    conn.close()
    data = {
        "user": u,
        "exported_at": datetime.now().isoformat(),
        "progress": [{"question_id": r["question_id"],
                      "solved": r["solved"],
                      "revision": r["revision"]} for r in rows]
    }
    return Response(
        json.dumps(data, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition":
                 f"attachment; filename={u}_backup_{datetime.now().strftime('%Y%m%d')}.json"}
    )

@app.route("/backup/restore", methods=["POST"])
def backup_restore():
    u = get_user()
    if not u: return redirect(url_for("home"))
    file = request.files.get("backup_file")
    if not file: return "No file uploaded", 400
    try:
        data = json.loads(file.read())
    except:
        return "❌ Invalid JSON file", 400
    if data.get("user") != u:
        return f"❌ Backup is for '{data.get('user')}' but you are logged in as '{u}'!", 400
    conn = db()
    conn.execute("DELETE FROM progress WHERE user=?", (u,))
    for item in data["progress"]:
        conn.execute(
            "INSERT INTO progress (user, question_id, solved, revision) VALUES (?,?,?,?)",
            (u, item["question_id"], item["solved"], item["revision"])
        )
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
