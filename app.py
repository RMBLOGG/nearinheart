import os
import uuid
import bcrypt
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from supabase import create_client, Client
from datetime import datetime, timezone

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ldr-secret-2024-bucin")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://mafnnqttvkdgqqxczqyt.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1hZm5ucXR0dmtkZ3FxeGN6cXl0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE4NzQyMDEsImV4cCI6MjA4NzQ1MDIwMX0.YRh1oWVKnn4tyQNRbcPhlSyvr7V_1LseWN7VjcImb-Y")

# Selalu pakai service key agar bisa bypass RLS
db: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY)

# ── Helper ────────────────────────────────────────────────────────────────────

def login_required():
    return "user_id" not in session

# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if login_required():
        return redirect(url_for("login"))
    return render_template("dashboard.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.get_json()
        username = data.get("username", "").strip().lower()
        password = data.get("password", "")
        try:
            res = db.table("app_users").select("*").eq("username", username).execute()
            if not res.data or len(res.data) == 0:
                return jsonify({"success": False, "error": "Username tidak ditemukan"})
            user = res.data[0]
            if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
                return jsonify({"success": False, "error": "Password salah"})
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["name"] = user.get("name", username)
            session["city"] = user.get("city", "")
            session["timezone"] = user.get("timezone", "Asia/Jakarta")
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.get_json()
        username = data.get("username", "").strip().lower()
        password = data.get("password", "")
        name = data.get("name", "").strip()
        city = data.get("city", "").strip()
        timezone_val = data.get("timezone", "Asia/Jakarta")
        if not username or not password or not name:
            return jsonify({"success": False, "error": "Lengkapi semua kolom"})
        if len(password) < 6:
            return jsonify({"success": False, "error": "Password minimal 6 karakter"})
        try:
            # Cek duplikat username
            existing = db.table("app_users").select("id").eq("username", username).execute()
            if existing.data and len(existing.data) > 0:
                return jsonify({"success": False, "error": "Username sudah dipakai"})
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            db.table("app_users").insert({
                "id": str(uuid.uuid4()),
                "username": username,
                "password_hash": password_hash,
                "name": name,
                "city": city,
                "timezone": timezone_val,
                "created_at": datetime.now(timezone.utc).isoformat()
            }).execute()
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ── Settings ──────────────────────────────────────────────────────────────────

@app.route("/settings", methods=["GET"])
def settings():
    if login_required():
        return redirect(url_for("login"))
    return render_template("settings.html")

@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    if login_required():
        return jsonify({"error": "Unauthorized"}), 401
    user_id = session["user_id"]

    if request.method == "GET":
        user = db.table("app_users").select("id,username,name,city,timezone").eq("id", user_id).execute()
        couple = db.table("couple_settings").select("*").eq("user_id", user_id).execute()
        return jsonify({"profile": user.data[0] if user.data else {}, "couple": couple.data[0] if couple.data else {}})

    data = request.get_json()
    db.table("app_users").update({
        "name": data.get("name"),
        "city": data.get("city"),
        "timezone": data.get("timezone"),
    }).eq("id", user_id).execute()

    existing = db.table("couple_settings").select("id").eq("user_id", user_id).execute()
    couple_data = {
        "user_id": user_id,
        "partner_username": data.get("partner_username", ""),
        "meet_date": data.get("meet_date") or None,
        "anniversary_date": data.get("anniversary_date") or None,
        "distance_km": data.get("distance_km", 0),
        "partner_city": data.get("partner_city", ""),
        "partner_timezone": data.get("partner_timezone", "Asia/Jakarta"),
    }
    if existing.data and len(existing.data) > 0:
        db.table("couple_settings").update(couple_data).eq("user_id", user_id).execute()
    else:
        couple_data["id"] = str(uuid.uuid4())
        db.table("couple_settings").insert(couple_data).execute()

    session["name"] = data.get("name")
    session["city"] = data.get("city")
    session["timezone"] = data.get("timezone", "Asia/Jakarta")
    return jsonify({"success": True})

# ── Dashboard API ─────────────────────────────────────────────────────────────

@app.route("/api/dashboard")
def api_dashboard():
    if login_required():
        return jsonify({"error": "Unauthorized"}), 401
    user_id = session["user_id"]

    couple = db.table("couple_settings").select("*").eq("user_id", user_id).maybe_single().execute()
    mood_me = db.table("moods").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(1).maybe_single().execute()
    my_status = db.table("statuses").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(1).maybe_single().execute()

    partner_mood = None
    partner_status = None
    partner_profile = None

    if couple.data and couple.data.get("partner_username"):
        partner = db.table("app_users").select("id,name,city,timezone,username").eq("username", couple.data["partner_username"]).maybe_single().execute()
        if partner.data:
            partner_profile = partner.data
            pm = db.table("moods").select("*").eq("user_id", partner.data["id"]).order("created_at", desc=True).limit(1).maybe_single().execute()
            partner_mood = pm.data
            ps = db.table("statuses").select("*").eq("user_id", partner.data["id"]).order("created_at", desc=True).limit(1).maybe_single().execute()
            partner_status = ps.data

    return jsonify({
        "couple": couple.data or {},
        "mood_me": mood_me.data,
        "partner_mood": partner_mood,
        "partner_status": partner_status,
        "my_status": my_status.data,
        "partner_profile": partner_profile,
        "my_name": session.get("name", ""),
        "my_city": session.get("city", ""),
        "my_timezone": session.get("timezone", "Asia/Jakarta"),
        "partner_timezone": partner_profile.get("timezone", "Asia/Jakarta") if partner_profile else (couple.data or {}).get("partner_timezone", "Asia/Jakarta"),
    })

# ── Mood ──────────────────────────────────────────────────────────────────────

@app.route("/api/mood", methods=["POST"])
def api_mood():
    if login_required():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    db.table("moods").insert({
        "id": str(uuid.uuid4()),
        "user_id": session["user_id"],
        "mood": data.get("mood"),
        "note": data.get("note", ""),
        "created_at": datetime.now(timezone.utc).isoformat()
    }).execute()
    return jsonify({"success": True})

# ── Status ────────────────────────────────────────────────────────────────────

@app.route("/api/status", methods=["POST"])
def api_status():
    if login_required():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    db.table("statuses").insert({
        "id": str(uuid.uuid4()),
        "user_id": session["user_id"],
        "status": data.get("status"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }).execute()
    return jsonify({"success": True})

# ── Love Letters ──────────────────────────────────────────────────────────────

@app.route("/letters")
def letters():
    if login_required():
        return redirect(url_for("login"))
    return render_template("letters.html")

@app.route("/api/letters", methods=["GET"])
def api_letters_get():
    if login_required():
        return jsonify({"error": "Unauthorized"}), 401
    user_id = session["user_id"]
    now = datetime.now(timezone.utc).isoformat()
    my_letters = db.table("letters").select("*").eq("sender_id", user_id).order("created_at", desc=True).execute()

    couple = db.table("couple_settings").select("partner_username").eq("user_id", user_id).maybe_single().execute()
    received = []
    if couple.data and couple.data.get("partner_username"):
        partner = db.table("app_users").select("id").eq("username", couple.data["partner_username"]).maybe_single().execute()
        if partner.data:
            received_raw = db.table("letters").select("*").eq("sender_id", partner.data["id"]).eq("recipient_id", user_id).order("created_at", desc=True).execute()
            for letter in (received_raw.data or []):
                unlock = letter.get("unlock_at")
                letter["locked"] = bool(unlock and unlock > now)
                received.append(letter)

    return jsonify({"sent": my_letters.data or [], "received": received})

@app.route("/api/letters", methods=["POST"])
def api_letters_post():
    if login_required():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    user_id = session["user_id"]

    couple = db.table("couple_settings").select("partner_username").eq("user_id", user_id).maybe_single().execute()
    recipient_id = None
    if couple.data and couple.data.get("partner_username"):
        partner = db.table("app_users").select("id").eq("username", couple.data["partner_username"]).maybe_single().execute()
        if partner.data:
            recipient_id = partner.data["id"]

    db.table("letters").insert({
        "id": str(uuid.uuid4()),
        "sender_id": user_id,
        "recipient_id": recipient_id,
        "title": data.get("title", "Surat Untukmu"),
        "content": data.get("content"),
        "unlock_at": data.get("unlock_at") or None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }).execute()
    return jsonify({"success": True})

# ── Journal ───────────────────────────────────────────────────────────────────

@app.route("/journal")
def journal():
    if login_required():
        return redirect(url_for("login"))
    return render_template("journal.html")

@app.route("/api/journal", methods=["GET"])
def api_journal_get():
    if login_required():
        return jsonify({"error": "Unauthorized"}), 401
    user_id = session["user_id"]

    couple = db.table("couple_settings").select("partner_username").eq("user_id", user_id).maybe_single().execute()
    partner_id = None
    if couple.data and couple.data.get("partner_username"):
        partner = db.table("app_users").select("id").eq("username", couple.data["partner_username"]).maybe_single().execute()
        if partner.data:
            partner_id = partner.data["id"]

    ids = [user_id] + ([partner_id] if partner_id else [])
    entries = db.table("journal").select("*").in_("user_id", ids).order("created_at", desc=True).execute()
    return jsonify({"entries": entries.data or [], "my_id": user_id})

@app.route("/api/journal", methods=["POST"])
def api_journal_post():
    if login_required():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    db.table("journal").insert({
        "id": str(uuid.uuid4()),
        "user_id": session["user_id"],
        "author_name": session.get("name", ""),
        "title": data.get("title"),
        "content": data.get("content"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reactions": []
    }).execute()
    return jsonify({"success": True})

@app.route("/api/journal/<entry_id>/react", methods=["POST"])
def api_journal_react(entry_id):
    if login_required():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    entry = db.table("journal").select("reactions").eq("id", entry_id).single().execute()
    reactions = entry.data.get("reactions") or []
    reactions.append({"user_id": session["user_id"], "emoji": data.get("emoji", "❤️")})
    db.table("journal").update({"reactions": reactions}).eq("id", entry_id).execute()
    return jsonify({"success": True})

# ── Memories ──────────────────────────────────────────────────────────────────

@app.route("/memories")
def memories():
    if login_required():
        return redirect(url_for("login"))
    return render_template("memories.html")

@app.route("/api/memories", methods=["GET"])
def api_memories_get():
    if login_required():
        return jsonify({"error": "Unauthorized"}), 401
    user_id = session["user_id"]

    couple = db.table("couple_settings").select("partner_username").eq("user_id", user_id).maybe_single().execute()
    partner_id = None
    if couple.data and couple.data.get("partner_username"):
        partner = db.table("app_users").select("id").eq("username", couple.data["partner_username"]).maybe_single().execute()
        if partner.data:
            partner_id = partner.data["id"]

    ids = [user_id] + ([partner_id] if partner_id else [])
    mems = db.table("memories").select("*").in_("user_id", ids).order("created_at", desc=True).execute()
    return jsonify({"memories": mems.data or []})

@app.route("/api/memories", methods=["POST"])
def api_memories_post():
    if login_required():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    db.table("memories").insert({
        "id": str(uuid.uuid4()),
        "user_id": session["user_id"],
        "author_name": session.get("name", ""),
        "image_url": data.get("image_url", ""),
        "caption": data.get("caption", ""),
        "created_at": datetime.now(timezone.utc).isoformat()
    }).execute()
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(debug=True)
