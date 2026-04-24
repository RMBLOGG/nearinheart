import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from supabase import create_client, Client
from datetime import datetime, timezone
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ldr-secret-2024-bucin")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://mafnnqttvkdgqqxczqyt.supabase.co")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1hZm5ucXR0dmtkZ3FxeGN6cXl0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE4NzQyMDEsImV4cCI6MjA4NzQ1MDIwMX0.YRh1oWVKnn4tyQNRbcPhlSyvr7V_1LseWN7VjcImb-Y")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            session["user_id"] = res.user.id
            session["email"] = res.user.email
            session["access_token"] = res.session.access_token
            profile = supabase.table("profiles").select("*").eq("user_id", res.user.id).single().execute()
            if profile.data:
                session["name"] = profile.data.get("name", email)
                session["partner_id"] = profile.data.get("partner_id", "")
                session["city"] = profile.data.get("city", "")
                session["timezone"] = profile.data.get("timezone", "Asia/Jakarta")
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        name = data.get("name")
        city = data.get("city")
        timezone_val = data.get("timezone", "Asia/Jakarta")
        try:
            res = supabase.auth.sign_up({"email": email, "password": password})
            user_id = res.user.id
            supabase.table("profiles").insert({
                "user_id": user_id,
                "name": name,
                "city": city,
                "timezone": timezone_val,
                "email": email
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
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("settings.html")

@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user_id = session["user_id"]

    if request.method == "GET":
        profile = supabase.table("profiles").select("*").eq("user_id", user_id).single().execute()
        couple = supabase.table("couple_settings").select("*").eq("user_id", user_id).maybe_single().execute()
        return jsonify({
            "profile": profile.data or {},
            "couple": couple.data or {}
        })

    data = request.get_json()
    # Update profile
    supabase.table("profiles").update({
        "name": data.get("name"),
        "city": data.get("city"),
        "timezone": data.get("timezone"),
    }).eq("user_id", user_id).execute()

    # Upsert couple settings
    existing = supabase.table("couple_settings").select("id").eq("user_id", user_id).maybe_single().execute()
    couple_data = {
        "user_id": user_id,
        "partner_email": data.get("partner_email", ""),
        "meet_date": data.get("meet_date", ""),
        "anniversary_date": data.get("anniversary_date", ""),
        "distance_km": data.get("distance_km", 0),
        "partner_city": data.get("partner_city", ""),
        "partner_timezone": data.get("partner_timezone", "Asia/Jakarta"),
    }
    if existing.data:
        supabase.table("couple_settings").update(couple_data).eq("user_id", user_id).execute()
    else:
        supabase.table("couple_settings").insert(couple_data).execute()

    session["name"] = data.get("name")
    session["city"] = data.get("city")
    session["timezone"] = data.get("timezone", "Asia/Jakarta")
    return jsonify({"success": True})

# ── Dashboard API ─────────────────────────────────────────────────────────────

@app.route("/api/dashboard")
def api_dashboard():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user_id = session["user_id"]

    couple = supabase.table("couple_settings").select("*").eq("user_id", user_id).maybe_single().execute()
    mood_me = supabase.table("moods").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(1).maybe_single().execute()

    partner_mood = None
    partner_status = None
    partner_profile = None

    if couple.data and couple.data.get("partner_email"):
        partner = supabase.table("profiles").select("*").eq("email", couple.data["partner_email"]).maybe_single().execute()
        if partner.data:
            partner_profile = partner.data
            pm = supabase.table("moods").select("*").eq("user_id", partner.data["user_id"]).order("created_at", desc=True).limit(1).maybe_single().execute()
            partner_mood = pm.data
            ps = supabase.table("statuses").select("*").eq("user_id", partner.data["user_id"]).order("created_at", desc=True).limit(1).maybe_single().execute()
            partner_status = ps.data

    my_status = supabase.table("statuses").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(1).maybe_single().execute()

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
    })

# ── Mood ──────────────────────────────────────────────────────────────────────

@app.route("/api/mood", methods=["POST"])
def api_mood():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    supabase.table("moods").insert({
        "user_id": session["user_id"],
        "mood": data.get("mood"),
        "note": data.get("note", ""),
        "created_at": datetime.now(timezone.utc).isoformat()
    }).execute()
    return jsonify({"success": True})

# ── Status ────────────────────────────────────────────────────────────────────

@app.route("/api/status", methods=["POST"])
def api_status():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    supabase.table("statuses").insert({
        "user_id": session["user_id"],
        "status": data.get("status"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }).execute()
    return jsonify({"success": True})

# ── Love Letters ──────────────────────────────────────────────────────────────

@app.route("/letters")
def letters():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("letters.html")

@app.route("/api/letters", methods=["GET"])
def api_letters_get():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user_id = session["user_id"]
    now = datetime.now(timezone.utc).isoformat()

    my_letters = supabase.table("letters").select("*").eq("sender_id", user_id).order("created_at", desc=True).execute()

    # Get partner id
    couple = supabase.table("couple_settings").select("partner_email").eq("user_id", user_id).maybe_single().execute()
    received = []
    if couple.data and couple.data.get("partner_email"):
        partner = supabase.table("profiles").select("user_id").eq("email", couple.data["partner_email"]).maybe_single().execute()
        if partner.data:
            partner_user_id = partner.data["user_id"]
            received_raw = supabase.table("letters").select("*").eq("sender_id", partner_user_id).eq("recipient_id", user_id).order("created_at", desc=True).execute()
            for letter in (received_raw.data or []):
                unlock = letter.get("unlock_at")
                letter["locked"] = unlock and unlock > now
                received.append(letter)

    return jsonify({"sent": my_letters.data or [], "received": received})

@app.route("/api/letters", methods=["POST"])
def api_letters_post():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    user_id = session["user_id"]

    couple = supabase.table("couple_settings").select("partner_email").eq("user_id", user_id).maybe_single().execute()
    recipient_id = None
    if couple.data and couple.data.get("partner_email"):
        partner = supabase.table("profiles").select("user_id").eq("email", couple.data["partner_email"]).maybe_single().execute()
        if partner.data:
            recipient_id = partner.data["user_id"]

    supabase.table("letters").insert({
        "id": str(uuid.uuid4()),
        "sender_id": user_id,
        "recipient_id": recipient_id,
        "title": data.get("title", "Surat Untukmu"),
        "content": data.get("content"),
        "unlock_at": data.get("unlock_at"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }).execute()
    return jsonify({"success": True})

# ── Journal ───────────────────────────────────────────────────────────────────

@app.route("/journal")
def journal():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("journal.html")

@app.route("/api/journal", methods=["GET"])
def api_journal_get():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user_id = session["user_id"]

    couple = supabase.table("couple_settings").select("partner_email").eq("user_id", user_id).maybe_single().execute()
    partner_id = None
    if couple.data and couple.data.get("partner_email"):
        partner = supabase.table("profiles").select("user_id, name").eq("email", couple.data["partner_email"]).maybe_single().execute()
        if partner.data:
            partner_id = partner.data["user_id"]

    entries = supabase.table("journal").select("*").in_("user_id", [user_id] + ([partner_id] if partner_id else [])).order("created_at", desc=True).execute()
    return jsonify({"entries": entries.data or [], "my_id": user_id})

@app.route("/api/journal", methods=["POST"])
def api_journal_post():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    supabase.table("journal").insert({
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
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    entry = supabase.table("journal").select("reactions").eq("id", entry_id).single().execute()
    reactions = entry.data.get("reactions") or []
    reactions.append({"user_id": session["user_id"], "emoji": data.get("emoji", "❤️")})
    supabase.table("journal").update({"reactions": reactions}).eq("id", entry_id).execute()
    return jsonify({"success": True})

# ── Memories ──────────────────────────────────────────────────────────────────

@app.route("/memories")
def memories():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("memories.html")

@app.route("/api/memories", methods=["GET"])
def api_memories_get():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user_id = session["user_id"]

    couple = supabase.table("couple_settings").select("partner_email").eq("user_id", user_id).maybe_single().execute()
    partner_id = None
    if couple.data and couple.data.get("partner_email"):
        partner = supabase.table("profiles").select("user_id").eq("email", couple.data["partner_email"]).maybe_single().execute()
        if partner.data:
            partner_id = partner.data["user_id"]

    memories = supabase.table("memories").select("*").in_("user_id", [user_id] + ([partner_id] if partner_id else [])).order("created_at", desc=True).execute()
    return jsonify({"memories": memories.data or []})

@app.route("/api/memories", methods=["POST"])
def api_memories_post():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    supabase.table("memories").insert({
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
