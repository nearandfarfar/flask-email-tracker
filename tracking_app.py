from flask import Flask, request, redirect, make_response, send_file
import io, sqlite3, os, time, html, base64

app = Flask(__name__)

@app.route("/")
def home():
    return "Flask Email Tracker is Running ✅<br>Endpoints: /o (open), /c (click)"



DB_PATH = os.environ.get("SUB_DB", "subscribers.db")

def db():
    return sqlite3.connect(DB_PATH)

def log_event(email, event, token, url=None):
    con = db()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO events(ts, email, event, token, url, ip, ua) VALUES(?,?,?,?,?,?,?)",
        (time.strftime("%Y-%m-%d %H:%M:%S"),
         email, event, token, url,
         request.headers.get("X-Forwarded-For", request.remote_addr),
         request.headers.get("User-Agent", ""))
    )
    con.commit()
    con.close()

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/unsubscribe")
def unsubscribe():
    token = request.args.get("u", "").strip()
    if not token:
        return make_response("Invalid unsubscribe link.", 400)
    con = db()
    cur = con.cursor()
    cur.execute("SELECT email, subscribed FROM subscribers WHERE token = ?", (token,))
    row = cur.fetchone()
    if not row:
        con.close()
        return make_response("This unsubscribe link is invalid or already used.", 404)
    email, subscribed = row
    if subscribed == 0:
        con.close()
        return f"<h2>{html.escape(email)}</h2><p>You're already unsubscribed.</p>"
    cur.execute("UPDATE subscribers SET subscribed=0, unsubscribed_at=? WHERE token=?",
                (time.strftime("%Y-%m-%d %H:%M:%S"), token))
    con.commit()
    con.close()
    log_event(email, "unsub", token, None)
    return (\
        "<html><body style=\"font-family: sans-serif;\">" \
        f"<h2>{html.escape(email)}</h2>" \
        "<p>You've been unsubscribed. We're sorry to see you go.</p>" \
        "</body></html>" \
    )

@app.get("/o")
def open_pixel():
    token = request.args.get("u", "").strip()
    email = None
    if token:
        con = db()
        cur = con.cursor()
        cur.execute("SELECT email FROM subscribers WHERE token=?", (token,))
        row = cur.fetchone()
        if row:
            email = row[0]
        con.close()
    log_event(email, "open", token, None)

    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMA"
        "ASsJTYQAAAAASUVORK5CYII="
    )
    return send_file(io.BytesIO(png_bytes), mimetype="image/png",
                     as_attachment=False, download_name="p.png")

@app.get("/c")
def click():
    token = request.args.get("u", "").strip()
    url = request.args.get("r", "").strip()
    if not url:
        return make_response("Missing redirect URL.", 400)
    email = None
    if token:
        con = db()
        cur = con.cursor()
        cur.execute("SELECT email FROM subscribers WHERE token=?", (token,))
        row = cur.fetchone()
        if row:
            email = row[0]
        con.close()
    log_event(email, "click", token, url)
    return redirect(url, code=302)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

