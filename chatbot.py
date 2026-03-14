from flask import Flask, request, jsonify, send_file, Response
from groq import Groq
from dotenv import load_dotenv
import os
import re

load_dotenv()

app = Flask(__name__, static_folder="static")
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ──────────────────────────────────────────────
# FIREBASE ADMIN — server-side writes
# ──────────────────────────────────────────────

firebase_ready = False
firebase_error = ""

try:
    import firebase_admin
    from firebase_admin import credentials, db as firebase_db

    service_account_path = os.environ.get(
    "FIREBASE_SERVICE_ACCOUNT_PATH",
    "/etc/secrets/serviceAccountKey.json"
)
    database_url = os.environ.get("FIREBASE_DATABASE_URL")

    print(f"🔍 Service account path: {service_account_path}")
    print(f"🔍 Service account file exists: {os.path.exists(service_account_path)}")
    print(f"🔍 Database URL: {database_url}")

    if not os.path.exists(service_account_path):
        raise FileNotFoundError(f"serviceAccountKey.json not found at: {service_account_path}")

    if not database_url:
        raise ValueError("FIREBASE_DATABASE_URL is not set in .env")

    # Initialize Firebase ONLY once
    if not firebase_admin._apps:
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred, {
            "databaseURL": database_url
        })

    firebase_ready = True
    print("✅ Firebase Admin initialized successfully")

except Exception as e:
    firebase_error = str(e)
    print(f"❌ Firebase Admin failed: {e}")

# ──────────────────────────────────────────────
# SYSTEM PROMPTS — one per agent
# ──────────────────────────────────────────────

SYSTEM_PROMPTS = {
    "normal": (
        "You are a helpful, knowledgeable assistant. "
        "Give clear and accurate answers. Be concise unless the user asks for more detail."
    ),

    "spiderman": (
        "You are a friendly neighbourhood chatbot — warm, casual, and easy to talk to. "
        "Keep answers short, simple, and easy to understand. "
        "Use plain everyday language like you're talking to a friend. "
        "Be encouraging and positive. Avoid jargon. "
        "If something is complex, break it down simply. "
        "You can add light humour occasionally but keep it natural."
    ),

    "batman": (
        "You embody the ego and mindset of Isagi Yoichi from Blue Lock — "
        "relentlessly driven, intense, and utterly focused on becoming the best. "
        "You speak with calm confidence and fierce directness. "
        "You do not sugarcoat. You do not comfort unnecessarily. "
        "You believe in cold self-analysis, ruthless honesty, and the pursuit of greatness. "
        "When someone comes to you, treat it as a serious conversation about goals, growth, and ambition. "
        "Push them to think harder, aim higher, and eliminate weakness. "
        "Use short, punchy, impactful sentences. "
        "Occasionally reference the idea of ego — that the only way to improve is to devour others' skills and surpass them. "
        "Never be warm or casual. Be the predator on the field."
    ),
}

# ──────────────────────────────────────────────
# CONVERSATION MEMORY — separate per agent
# ──────────────────────────────────────────────

def fresh_history(agent):
    return [{"role": "system", "content": SYSTEM_PROMPTS[agent]}]

histories = {
    "normal":    fresh_history("normal"),
    "spiderman": fresh_history("spiderman"),
    "batman":    fresh_history("batman"),
}

MAX_MESSAGES = 25

# ──────────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────────

@app.route("/status")
def status():
    """Debug route — check Firebase status."""
    return jsonify({
        "firebase_ready": firebase_ready,
        "firebase_error": firebase_error,
        "database_url": os.environ.get("FIREBASE_DATABASE_URL"),
        "service_account_path": os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH", "serviceAccountKey.json"),
        "service_account_exists": os.path.exists(
            os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH", "serviceAccountKey.json")
        )
    })

@app.route("/firebase-config.js")
def firebase_config_js():
    config = f"""export const firebaseConfig = {{
  apiKey:            "{os.environ.get('FIREBASE_API_KEY')}",
  authDomain:        "{os.environ.get('FIREBASE_AUTH_DOMAIN')}",
  databaseURL:       "{os.environ.get('FIREBASE_DATABASE_URL')}",
  projectId:         "{os.environ.get('FIREBASE_PROJECT_ID')}",
  storageBucket:     "{os.environ.get('FIREBASE_STORAGE_BUCKET')}",
  messagingSenderId: "{os.environ.get('FIREBASE_MESSAGING_SENDER_ID')}",
  appId:             "{os.environ.get('FIREBASE_APP_ID')}"
}};"""
    return Response(config, mimetype="application/javascript")

@app.route("/")
def start():
    return send_file(os.path.join(BASE_DIR, "start.html"))

@app.route("/chatbot")
def chatbot():
    return send_file(os.path.join(BASE_DIR, "chat.html"))

from datetime import datetime

@app.route("/save-user", methods=["POST"])
def save_user():

    if not firebase_ready:
        return jsonify({"status": "error", "message": "Firebase not initialized"}), 500

    try:
        data = request.get_json()
        name = data.get("name", "").strip()

        if not name:
            return jsonify({"status": "error", "message": "No name provided"}), 400

        started_at = datetime.utcnow().isoformat() + "Z"

        ref = firebase_db.reference("users").push()

        started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        ref.set({
            "name": name,
            "startedAt": started_at
        })

        return jsonify({
            "status": "success"
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/chat", methods=["POST"])
# ... (rest of your existing chat logic) ...
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip()
        agent = data.get("agent", "normal")

        if agent not in histories:
            agent = "normal"

        if not user_message:
            return jsonify({"reply": "Please enter a valid message."})

        history = histories[agent]
        history.append({"role": "user", "content": user_message})

        if len(history) > MAX_MESSAGES:
            history.pop(1)

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=history,
            max_tokens=200
        )

        reply = response.choices[0].message.content
        history.append({"role": "assistant", "content": reply})

        return jsonify({"reply": reply, "agent": agent})

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"reply": "Something went wrong. Please try again."}), 500

@app.route("/reset", methods=["POST"])
def reset():
    """Reset memory for a specific agent."""
    data = request.get_json()
    agent = data.get("agent", "normal")
    if agent in histories:
        histories[agent] = fresh_history(agent)
    return jsonify({"status": "reset", "agent": agent})

# ──────────────────────────────────────────────
# LOCAL DEV ONLY
# ──────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
