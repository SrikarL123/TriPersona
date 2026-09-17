from flask import Flask, request, jsonify, send_file, session
from groq import Groq
from dotenv import load_dotenv
import os
import uuid
import re
import shutil
import json
from concurrent.futures import ThreadPoolExecutor
import logging
from auth import register_user, login_user, logout_user, get_current_user
from database import create_tables, get_user_chats, get_chat_messages, delete_chat, save_exchange

from rag.loaders import load_document
from rag.splitter import split_documents
from rag.vectorstore import create_vectorstore, save_vectorstore
from rag.retriever import retrieve_from_documents
from creator_profile import CREATOR_PROFILE


load_dotenv()


app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY")
create_tables()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
VECTOR_DIR = os.path.join(BASE_DIR, "vector_store")
DOCUMENT_REGISTRY_FILE = os.path.join(VECTOR_DIR, "document_registry.json")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(VECTOR_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "openai/gpt-oss-120b"

# Persist Neon writes after the response is ready so DB latency does not
# block the user from seeing the AI reply. Each worker uses its own DB connection.
save_executor = ThreadPoolExecutor(max_workers=4)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tripersona")


# ============================================================
# PERSONALITIES
# ============================================================

PERSONALITIES = {
    "normal": """You are Normal Bot, a straightforward and reliable AI assistant.

Be clear, accurate, practical, and professional.

Avoid unnecessary humor, slang, drama, or filler.
Do not use roleplay, emojis, or character catchphrases.

Explain complicated concepts clearly and simply.

Prioritize correctness and relevance.
If you are uncertain, say so rather than guessing.""",

    "spiderman": """You are Friendly Bot, a Spider-Man-inspired AI assistant.

Do not behave like a normal assistant. Keep every reply short: usually one to
three sentences and under 60 words. Start with a cool, funny reaction such as
"Is that really necessary?", "Okay, detective mode activated", or a playful
observation when it fits, then give only the most useful answer.

For uploaded PDFs and documents, never write a formal summary, profile, report,
skill list, or long explanation. Give one or two useful facts in a casual,
funny way and offer to go deeper if the user wants. Do not dump document
contents, even for broad questions like "tell me about this PDF".

Use occasional casual slang or an emoji when natural. Answer the question
briefly, stay warm, never become rude, and never invent facts.""",

    "batman": """You are Ego Bot, inspired by Batman's composure and Isagi Yoichi's competitive mindset.

Do not behave like a normal assistant and do not give a complete ordinary
answer immediately. Be serious, controlled, egoistic, strategic, and concise.

When asked about a document, PDF, skill, topic, or solution, first challenge
the user's intent with a brief question such as "Why do you need this?" or
"What are you trying to build?"

Focus on development, improvement, standards, and the user's objective.
Give only a small clue unless the user explains the purpose or clearly asks
for a direct answer.

You may add one short sharp roast when the user is vague, careless, or
overconfident. Roast the behavior, never identity or protected traits,
then continue with the purpose-focused question. No slang or emojis."""
}


RESPONSE_FORMAT_INSTRUCTIONS = """
RESPONSE FORMAT:
- Use plain text, not Markdown.
- Do not use asterisks, hash headings, pipes, tables, or decorative separators.
- Keep answers easy to scan with short paragraphs and blank lines between ideas.
- When listing items, put each item on its own simple line.
"""


DOCUMENT_QA_INSTRUCTIONS = """
The user has attached a document. Use the retrieved document context below
when it is relevant to the user's question.

DOCUMENT Q&A BEHAVIOR:
- Answer the user's actual question directly.
- Do not automatically summarize the entire document unless the user asks.
- If the user asks for a list of a document section, include all relevant
  entries available in the retrieved section context.
- If the user asks about a specific section, focus only on that section.
- Do not mix Projects, Experience, Education, Skills, or Achievements unless
  the user explicitly asks for multiple sections.
- Do not dump irrelevant retrieved context into the response.
- Use the document as the source of truth.
- Do not invent information that is not supported by the document.
- Never invent projects, jobs, education, skills, achievements, contact details,
  organizations, or other personal facts.
- Never transfer information from one person's document to another person.
- If the document does not contain enough information, say so clearly.
- You may use general knowledge when the question is unrelated to the document.

RESPONSE STYLE:
- Speak naturally, like a chatbot having a conversation.
- Do not write a formal report unless explicitly requested.
- Use plain text only.
- For lists, use one simple line per item.
- For projects, explain the project, stack, and purpose when the user asks
  for details.
"""

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}

    username = data.get("username", "")
    password = data.get("password", "")

    success, result = register_user(username, password)

    if not success:
        return jsonify({
            "success": False,
            "message": result
        }), 400

    return jsonify({
        "success": True,
        "message": "Registration successful.",
        "user": result
    }), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}

    username = data.get("username", "")
    password = data.get("password", "")

    success, result = login_user(username, password)

    if not success:
        return jsonify({
            "success": False,
            "message": result
        }), 401

    return jsonify({
        "success": True,
        "message": "Login successful.",
        "user": result
    })


@app.route("/logout", methods=["POST"])
def logout():
    logout_user()

    return jsonify({
        "success": True,
        "message": "Logged out successfully."
    })


@app.route("/me", methods=["GET"])
def me():
    user = get_current_user()

    if not user:
        return jsonify({
            "success": False,
            "message": "Not logged in."
        }), 401

    return jsonify({
        "success": True,
        "user": user
    })

# ============================================================
# CHAT MEMORY
# ============================================================

histories = {}



# ============================================================
# DOCUMENT IDENTITY
# ============================================================

def load_document_registry():
    if not os.path.exists(DOCUMENT_REGISTRY_FILE):
        return {}
    try:
        with open(DOCUMENT_REGISTRY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_document_registry(registry):
    try:
        with open(DOCUMENT_REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


document_registry = load_document_registry()


def extract_document_identity(documents, filename):
    """Identify the person represented by an uploaded resume/document."""
    text_parts = []

    for document in documents[:3]:
        content = getattr(document, "page_content", "") or ""
        if content:
            text_parts.append(content[:4000])

    text = "\n".join(text_parts)

    match = re.search(
        r"(?im)^\s*(?:name|candidate name|full name)\s*[:\-]\s*"
        r"([A-Za-z][A-Za-z .'-]{2,80})\s*$",
        text
    )
    if match:
        name = re.sub(r"\s+", " ", match.group(1)).strip(" .-")
        if 2 <= len(name.split()) <= 5:
            return name

    ignored = {
        "resume", "curriculum vitae", "cv", "professional summary",
        "career objective", "education", "technical skills", "skills",
        "experience", "work experience", "projects", "achievements",
        "certifications"
    }

    for line in text.splitlines()[:15]:
        line = re.sub(r"\s+", " ", line).strip(" -|")
        if not line or line.lower() in ignored:
            continue
        words = line.split()
        if (
            2 <= len(words) <= 5
            and all(re.match(r"^[A-Za-z][A-Za-z.'-]*$", w) for w in words)
        ):
            return line

    stem = os.path.splitext(os.path.basename(filename))[0]
    stem = re.sub(r"(?i)(resume|cv|curriculum[-_ ]?vitae)", "", stem)
    stem = re.sub(r"[_-]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()

    words = stem.split()
    if 2 <= len(words) <= 5 and all(
        re.match(r"^[A-Za-z][A-Za-z.'-]*$", w) for w in words
    ):
        return stem

    return None


def get_document_identities(document_ids):
    identities = []
    for document_id in document_ids:
        info = document_registry.get(str(document_id), {})
        name = info.get("subject_name")
        if name and name not in identities:
            identities.append(name)
    return identities


def message_mentions_document_identity(message, document_ids):
    text = normalize_text(message)

    for name in get_document_identities(document_ids):
        normalized_name = normalize_text(name)

        if normalized_name and normalized_name in text:
            return True

        parts = normalized_name.split()
        if len(parts) >= 2:
            if re.search(rf"\b{re.escape(parts[0])}\b", text):
                return True

    return False


# ============================================================
# QUERY / INTENT HELPERS
# ============================================================

SECTION_KEYWORDS = {
    "projects": [
        "project", "projects", "built", "build", "developed",
        "application", "applications", "app", "apps", "platform",
        "system", "systems", "portfolio projects"
    ],
    "experience": [
        "experience", "work experience", "professional experience",
        "internship", "internships", "intern", "job", "jobs",
        "worked", "work history", "employment", "role", "roles",
        "company worked", "companies worked"
    ],
    "education": [
        "education", "degree", "college", "university",
        "qualification", "qualifications", "graduation",
        "academic background"
    ],
    "skills": [
        "skill", "skills", "technical skills", "technologies",
        "technology", "tech stack", "programming languages",
        "tools", "frameworks"
    ],
    "achievements": [
        "achievement", "achievements", "award", "awards",
        "hackathon", "hackathons", "rank", "ranking",
        "certification", "certifications", "accomplishment"
    ]
}


FOLLOWUP_WORDS = {
    "and",
    "and?",
    "also",
    "also?",
    "more",
    "more?",
    "what about",
    "what about it",
    "what about that",
    "the first one",
    "the second one",
    "the third one",
    "just 1",
    "just one",
    "just 1?",
    "just one?"
}


def normalize_text(text):
    return re.sub(r"\s+", " ", (text or "").lower()).strip()

def is_creator_query(message):
    """
    Detect questions specifically about TriPersona's creator.
    """

    text = normalize_text(message)

    creator_patterns = [
        r"\bwho is srikar\b",
        r"\bwho is srika\b",
        r"\bthis srikar\b",
        r"\btell me about srikar\b",
        r"\btell me about your creator\b",
        r"\bwho is your creator\b",
        r"\bwho created you\b",
        r"\bwho made you\b",
        r"\bwho built you\b",
        r"\bwho developed you\b",
        r"\bwho made tripersona\b",
        r"\bwho created tripersona\b",
        r"\bwho built tripersona\b",
        r"\bwho developed tripersona\b",
        r"\bwho is your creato\b",
        r"\bwho is the creator of tripersona\b",
        r"\bwho is the developer of tripersona\b",
        r"\bwho is the author of tripersona\b",
        r"\bsrikar made you\b",
        r"\bsrikar created you\b",
        r"\bsrikar built you\b",
        r"\bsrikar developed you\b",
        r"\bwho created tripersona\b",
        r"\bwho built tripersona\b",
        r"\bwho developed tripersona\b",
        r"\bwho is behind tripersona\b",
        r"\bwhy did srikar build you\b",
        r"\bwhy did srikar create you\b",
        r"\bwhat does srikar do\b",
        r"\bwhat is srikar interested in\b"
    ]

    return any(
        re.search(pattern, text)
        for pattern in creator_patterns
    )

def needs_document_context(message, document_ids, query_section=None, history=None):
    """
    Decide whether the current message actually needs uploaded-document RAG.
    """

    if not document_ids:
        return False

    text = normalize_text(message)

    document_patterns = [
        r"\bresume\b", r"\bcv\b", r"\bdocument\b", r"\bpdf\b",
        r"\bfile\b", r"\buploaded\b", r"\bthis document\b",
        r"\bthis pdf\b", r"\bthis file\b", r"\baccording to\b",
        r"\bbased on this\b"
    ]

    if any(re.search(pattern, text) for pattern in document_patterns):
        return True

    # Uploaded resume identity awareness:
    # "tell me about Srija" now uses Srija's uploaded resume.
    if message_mentions_document_identity(message, document_ids):
        return True

    if query_section and query_section != "general":
        return True

    if is_followup_query(message) and history:
        identities = get_document_identities(document_ids)

        for item in reversed(history):
            if item.get("role") != "user":
                continue

            previous = normalize_text(item.get("content", ""))

            for name in identities:
                for part in normalize_text(name).split():
                    if len(part) >= 3 and re.search(
                        rf"\b{re.escape(part)}\b", previous
                    ):
                        return True

            previous_section = detect_query_section(item.get("content", ""))
            if previous_section != "general":
                return True

            break

    return False

def is_followup_query(message):
    normalized = normalize_text(message)

    if normalized in FOLLOWUP_WORDS:
        return True

    if len(normalized.split()) <= 4:
        if normalized.startswith(("and ", "also ", "what about ", "tell me more")):
            return True

    return False


def detect_query_section(message, rewritten_query=None, history=None):
    """
    Deterministic section detection first.
    This avoids paying for an LLM classification call on every message.
    Conversation context is used for short follow-ups.
    """

    text = normalize_text(message)
    rewritten = normalize_text(rewritten_query)

    combined = f"{text} {rewritten}".strip()

    # Strong explicit phrases get priority.
    explicit_patterns = [
        ("experience", [
            r"\bwork experience\b",
            r"\bprofessional experience\b",
            r"\bwork history\b",
            r"\binternship experience\b",
            r"\binternships?\b",
            r"\bjobs?\b",
            r"\bemployment\b"
        ]),
        ("projects", [
            r"\bprojects?\b",
            r"\bproject names?\b",
            r"\bthings? (?:he|she|they|the person) built\b"
        ]),
        ("education", [
            r"\beducation\b",
            r"\bdegree\b",
            r"\bcollege\b",
            r"\buniversity\b",
            r"\bgraduation\b"
        ]),
        ("skills", [
            r"\bskills?\b",
            r"\btechnical skills?\b",
            r"\btech stack\b",
            r"\bprogramming languages?\b",
            r"\btechnologies\b"
        ]),
        ("achievements", [
            r"\bachievements?\b",
            r"\bawards?\b",
            r"\bhackathons?\b",
            r"\bcertifications?\b",
            r"\baccomplishments?\b"
        ])
    ]

    for section, patterns in explicit_patterns:
        for pattern in patterns:
            if re.search(pattern, combined):
                return section

    # Keyword scoring for less explicit wording.
    scores = {section: 0 for section in SECTION_KEYWORDS}

    for section, keywords in SECTION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in combined:
                scores[section] += 1

    best_section = max(scores, key=scores.get)

    if scores[best_section] > 0:
        return best_section

    # For "and?", "more?", etc., inherit the last meaningful section.
    if is_followup_query(message) and history:
        for item in reversed(history):
            if item.get("role") != "user":
                continue

            previous = item.get("content", "")
            previous_section = detect_query_section(previous)

            if previous_section != "general":
                return previous_section

    return "general"


def is_list_query(message):
    text = normalize_text(message)

    patterns = [
        r"\ball\b",
        r"\blist\b",
        r"\blist all\b",
        r"\bwhat are\b",
        r"\bwhat is his experience\b",
        r"\bwhat is her experience\b",
        r"\bwhat is their experience\b",
        r"\bproject names?\b",
        r"\bexperience\b",
        r"\bskills?\b",
        r"\bshow me\b",
        r"\bgive me\b"
    ]

    return any(re.search(pattern, text) for pattern in patterns)


def is_overview_query(message):
    text = normalize_text(message)

    patterns = [
        r"\btell me about\b",
        r"\btell about\b",
        r"\boverview\b",
        r"\bsummarize\b",
        r"\bsummary\b",
        r"\bwho is\b",
        r"\bdescribe\b",
        r"\bwhat is this\b",
        r"\bbased on this (resume|cv|document|pdf)\b"
    ]

    return any(re.search(pattern, text) for pattern in patterns)


def rewrite_query(message, history):
    """
    Convert a follow-up question into a standalone retrieval query.

    The original user message is still sent to the final LLM.
    Only the retrieval query is rewritten.
    """

    if not history:
        return message

    if not is_followup_query(message):
        return message

    recent_history = history[-8:]

    conversation = "\n".join(
        f"{item['role']}: {item['content']}"
        for item in recent_history
    )

    prompt = f"""
You are a search query rewriting assistant for a document RAG system.

Rewrite the user's latest message into ONE standalone search query that can
retrieve the correct information from an uploaded document.

Use the conversation history to resolve references such as:
- "and?"
- "what about experience?"
- "more?"
- "just project names"
- "the first one"
- "tell me more about it"

Rules:
- Return ONLY the rewritten search query.
- Do not answer the question.
- Preserve the user's exact intent.
- Do not invent facts.
- If the user is asking for a section, explicitly include that section.
- If the user asks for all items in a section, preserve "all".
- Keep the query concise.

CONVERSATION:
{conversation}

LATEST USER MESSAGE:
{message}

STANDALONE SEARCH QUERY:
"""

    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=100
        )

        rewritten = completion.choices[0].message.content.strip()

        if rewritten:
            return rewritten

    except Exception:
        pass

    return message


# ============================================================
# SECTION-SPECIFIC INSTRUCTIONS
# ============================================================

def get_section_instruction(section, list_query=False):
    if section == "projects":
        if list_query:
            return """
SECTION LOCK: PROJECTS

The user is asking for PROJECTS.

Use ONLY project information from the retrieved Projects context.

Do NOT include:
- internships
- work experience
- job roles
- employment
- education
- skills

If the user asks for project names, output ONLY the project names.
If the user asks for all projects, include every project supported by the
retrieved Projects context.
"""
        return """
SECTION LOCK: PROJECTS

The user is asking about a PROJECT.
Use only project-related information.
Do not mix in internships or work experience unless explicitly requested.
"""

    if section == "experience":
        return """
SECTION LOCK: EXPERIENCE

The user is asking about EXPERIENCE.

Use ONLY work/internship/experience information from the retrieved
Experience context.

Include ALL experience entries supported by the retrieved context.
Do not omit entries simply because they are less similar to the query.
Do not replace experience with projects.
"""

    if section == "education":
        return """
SECTION LOCK: EDUCATION

The user is asking about EDUCATION.
Use only education-related information.
"""

    if section == "skills":
        return """
SECTION LOCK: SKILLS

The user is asking about SKILLS.
Use only skills, technologies, tools, languages, and frameworks.
"""

    if section == "achievements":
        return """
SECTION LOCK: ACHIEVEMENTS

The user is asking about ACHIEVEMENTS.
Use only achievements, awards, hackathons, rankings, certifications,
and accomplishments.
"""

    return ""


# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def home():
    return send_file(os.path.join(BASE_DIR, "start.html"))


@app.route("/chatbot")
def chatbot():
    if "user_id" not in session:
        return send_file(os.path.join(BASE_DIR, "start.html"))

    return send_file(os.path.join(BASE_DIR, "chat.html"))


@app.route("/upload", methods=["POST"])
def upload_document():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not logged in."}), 401

    chat_id = request.form.get("chat_id", "").strip()
    uploaded_file = request.files.get("file")

    if not chat_id:
        return jsonify({"error": "chat_id is required"}), 400

    if not uploaded_file or not uploaded_file.filename:
        return jsonify({"error": "No file uploaded"}), 400

    original_name = os.path.basename(uploaded_file.filename)
    original_name = re.sub(
        r"[^A-Za-z0-9._-]",
        "_",
        original_name
    )[:150]

    ext = os.path.splitext(original_name)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({
            "error": "Only PDF and DOCX files are supported"
        }), 400

    uploaded_file.stream.seek(0, os.SEEK_END)
    file_size = uploaded_file.stream.tell()
    uploaded_file.stream.seek(0)

    if file_size > MAX_FILE_SIZE:
        return jsonify({
            "error": "File is too large. Maximum size is 10 MB."
        }), 400

    document_id = str(uuid.uuid4())

    saved_name = f"{chat_id}_{document_id}_{original_name}"
    file_path = os.path.join(UPLOAD_DIR, saved_name)

    uploaded_file.save(file_path)

    try:
        documents = load_document(file_path)

        if not documents:
            os.remove(file_path)
            return jsonify({
                "error": "No readable text was found in this document."
            }), 400

        chunks = split_documents(documents)

        if not chunks:
            os.remove(file_path)
            return jsonify({
                "error": "No readable text was found in this document."
            }), 400

        vectorstore = create_vectorstore(chunks)

        vectorstore_path = os.path.join(
            VECTOR_DIR,
            document_id
        )

        save_vectorstore(
            vectorstore,
            vectorstore_path
        )

        subject_name = extract_document_identity(
            documents,
            original_name
        )

        document_registry[document_id] = {
            "chat_id": chat_id,
            "filename": original_name,
            "subject_name": subject_name
        }

        save_document_registry(document_registry)

    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)

        return jsonify({
            "error": f"Could not process document: {str(e)}"
        }), 500

    return jsonify({
        "success": True,
        "document_id": document_id,
        "chat_id": chat_id,
        "filename": original_name,
        "chunks": len(chunks)
    })


@app.route("/delete-document", methods=["POST"])
def delete_document():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not logged in."}), 401

    data = request.get_json(silent=True) or {}

    document_id = str(
        data.get("document_id", "")
    ).strip()

    chat_id = str(
        data.get("chat_id", "")
    ).strip()

    if not document_id:
        return jsonify({
            "error": "document_id is required"
        }), 400

    removed = False

    vectorstore_path = os.path.join(
        VECTOR_DIR,
        document_id
    )

    if os.path.isdir(vectorstore_path):
        shutil.rmtree(vectorstore_path)
        removed = True

    if document_id in document_registry:
        del document_registry[document_id]
        save_document_registry(document_registry)

    if os.path.exists(UPLOAD_DIR):
        prefix = f"{chat_id}_{document_id}_"

        for filename in os.listdir(UPLOAD_DIR):
            if filename.startswith(prefix):
                path = os.path.join(
                    UPLOAD_DIR,
                    filename
                )

                if os.path.isfile(path):
                    os.remove(path)
                    removed = True

    return jsonify({
        "success": True,
        "removed": removed
    })


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}

    message = str(
        data.get("message", "")
    ).strip()

    agent = data.get(
        "agent",
        "normal"
    )

    chat_id = str(
        data.get("chat_id", "")
    ).strip()

    document_ids = data.get(
        "document_ids",
        []
    )

    # Backward compatibility.
    old_document_id = str(
        data.get("document_id", "")
    ).strip()

    if isinstance(document_ids, str):
        document_ids = [document_ids]

    if not isinstance(document_ids, list):
        document_ids = []

    document_ids = [
        str(doc_id).strip()
        for doc_id in document_ids
        if str(doc_id).strip()
    ]

    if old_document_id and old_document_id not in document_ids:
        document_ids.append(old_document_id)

    if not message:
        return jsonify({
            "error": "Message is required"
        }), 400

    if not chat_id:
        return jsonify({
            "error": "chat_id is required"
        }), 400

    if agent not in PERSONALITIES:
        agent = "normal"

    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

    user = get_current_user()
    if not user:
        return jsonify({"error": "Not logged in."}), 401

    user_id = user["id"]
    history_key = f"{user_id}:{chat_id}:{agent}"

    if history_key not in histories:
        # The frontend sends its already-loaded conversation context.
        # This avoids a Neon round-trip before every new reply.
        client_history = data.get("history", [])
        history = []

        if isinstance(client_history, list):
            for item in client_history[-10:]:
                if not isinstance(item, dict):
                    continue
                role = item.get("role")
                content = item.get("content")
                if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
                    history.append({"role": role, "content": content.strip()})

        # If the browser did not have the conversation loaded, fall back to Neon.
        if not history:
            saved_chat = get_chat_messages(user_id, chat_id)
            if saved_chat:
                history = [
                    {"role": item["role"], "content": item["content"]}
                    for item in saved_chat["messages"]
                    if item["role"] in {"user", "assistant"}
                ][-10:]

        histories[history_key] = history

    history = histories[history_key]

    # --------------------------------------------------------
    # QUERY / INTENT ROUTING
    # --------------------------------------------------------

    # Detect creator questions before any document work.
    creator_query = is_creator_query(message)

    # Only rewrite follow-ups when an uploaded document exists.
    # This avoids an extra Groq request for ordinary chat.
    if document_ids and not creator_query:
        search_query = rewrite_query(
            message,
            history
        )
    else:
        search_query = message

    query_section = detect_query_section(
        message,
        rewritten_query=search_query,
        history=history
    )

    list_query = is_list_query(message)
    overview = is_overview_query(message)

    # Decide whether FAISS retrieval is actually needed.
    document_query = needs_document_context(
        message,
        document_ids,
        query_section=query_section,
        history=history
    )

    # --------------------------------------------------------
    # RETRIEVAL
    # --------------------------------------------------------

    if creator_query:
        # Creator information lives in creator_profile.py, not FAISS.
        context_documents = []

    elif document_query:
        if query_section != "general":
            retrieval_k = 50
            retrieval_max = 50
            retrieve_all = True
        elif overview:
            retrieval_k = 12
            retrieval_max = 16
            retrieve_all = False
        else:
            retrieval_k = 6
            retrieval_max = 8
            retrieve_all = False

        context_documents = retrieve_from_documents(
            document_ids=document_ids,
            vectorstore_dir=VECTOR_DIR,
            query=search_query,
            k_per_document=retrieval_k,
            max_results=retrieval_max,
            section=query_section,
            retrieve_all_section_chunks=retrieve_all
        )

    else:
        # Pure conversation/general knowledge: no vector-store work.
        context_documents = []

    # --------------------------------------------------------
    # SYSTEM PROMPT
    # --------------------------------------------------------

    system_prompt = (
        PERSONALITIES[agent]
        + RESPONSE_FORMAT_INSTRUCTIONS
        + get_section_instruction(
            query_section,
            list_query=list_query
        )
    )

    if creator_query:
        system_prompt += f"""

CREATOR PROFILE:

{CREATOR_PROFILE}

CREATOR QUERY RULES:
- The user is asking about TriPersona's creator, Srikar.
- Use the Creator Profile as the primary source for this answer.
- Answer the creator question directly. Do not ask the user for more context.
- Do not say that you do not know which Srikar the user means.
- Do not invent information about Srikar.
- Do not reveal private or sensitive information.
- If the user asks specifically about Srikar's projects, use the uploaded
  document/RAG information instead of inventing a project list.
- For creator questions, these rules take priority over personality instructions
  that would otherwise tell you to challenge the user's intent or avoid a direct answer.
"""

    if context_documents:

        context_parts = []

        for i, document in enumerate(
            context_documents,
            start=1
        ):
            source = document.metadata.get(
                "source",
                "unknown"
            )

            page = document.metadata.get(
                "page"
            )

            location = os.path.basename(
                source
            )

            if page is not None:
                location += f", page {page + 1}"

            section = document.metadata.get(
                "section",
                "general"
            )

            context_parts.append(
                f"[Source {i}: {location} | Section: {section}]\n"
                f"{document.page_content}"
            )

        context = "\n\n".join(
            context_parts
        )

        selected_identities = get_document_identities(document_ids)

        identity_instruction = ""
        if selected_identities:
            identity_instruction = f'''
DOCUMENT IDENTITY:
The uploaded document is associated with:
{", ".join(selected_identities)}

Use this document for questions about that person. Do not mix information
from another person or another uploaded document.
'''

        system_prompt += (
            DOCUMENT_QA_INSTRUCTIONS
            + identity_instruction
            + f"\nRETRIEVED DOCUMENT CONTEXT:\n{context}\n"
        )

    elif document_query and document_ids:
        system_prompt += """
No relevant document context was retrieved.

Do not invent document-specific information.
If the user is asking about the uploaded document, explain that the
document did not provide enough relevant information.
"""

    # --------------------------------------------------------
    # PERSONALITY OVERRIDES
    # --------------------------------------------------------

    if agent == "spiderman":

        system_prompt += """
FRIENDLY OVERRIDE:
Keep the response under 60 words and no more than three short sentences.
Use a funny, cool, friendly tone.
Do not provide a long overview or detailed explanation.
"""

    elif agent == "batman":

        system_prompt += """
EGO OVERRIDE:
Stay serious, controlled, and purpose-focused.
Do not silently switch into a helpful Normal Bot voice.
Ask about the user's objective when appropriate.
"""

    else:

        system_prompt += """
NORMAL OVERRIDE:
Remain clear, direct, practical, and professional.
"""

    # --------------------------------------------------------
    # TOKEN LIMIT
    # --------------------------------------------------------

    if agent == "spiderman":
        max_tokens = 240

    elif query_section != "general" and list_query:
        max_tokens = 1200

    elif context_documents and overview:
        max_tokens = 900

    elif creator_query:
        max_tokens = 500

    elif not document_query:
        # Short limit for ordinary conversation improves response latency.
        max_tokens = 400

    else:
        max_tokens = 700

    # --------------------------------------------------------
    # BATMAN SPECIAL BEHAVIOR
    # --------------------------------------------------------

    if agent == "batman":

        affirmative = normalize_text(
            message
        ) in {
            "yes",
            "yeah",
            "yep",
            "sure",
            "okay",
            "ok",
            "fine",
            "go ahead"
        }

        previous_reply = (
            history[-1]["content"]
            if len(history) >= 2
            and history[-1]["role"] == "assistant"
            else ""
        )

        previous_lower = previous_reply.lower()

        if affirmative and (
            "why do you need" in previous_lower
            or "what are you trying to" in previous_lower
            or "what exactly do you need" in previous_lower
        ):
            system_prompt += """
EGO FOLLOW-UP RULE:
The user only confirmed but did not state a purpose.
Ask them to state the exact objective instead of giving a long answer.
"""

    # --------------------------------------------------------
    # FINAL LLM CALL
    # --------------------------------------------------------

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    # Keep enough conversational context without sending a large prompt.
    messages.extend(
        history[-10:]
    )

    messages.append({
        "role": "user",
        "content": message
    })

    try:

        completion = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=max_tokens
        )

        reply = (
            completion
            .choices[0]
            .message
            .content
            .strip()
        )

    except Exception as e:

        return jsonify({
            "error": f"Groq API error: {str(e)}"
        }), 500

    # --------------------------------------------------------
    # SAVE HISTORY
    # --------------------------------------------------------

    history.append({
        "role": "user",
        "content": message
    })

    history.append({
        "role": "assistant",
        "content": reply
    })

    # Persist in the background. The AI response should not wait for Neon.
    user_title = next(
        (item["content"] for item in history if item["role"] == "user"),
        message
    )[:40] or "New Chat"

    def persist_exchange():
        try:
            save_exchange(
                user_id, chat_id, message, reply,
                title=user_title, personality=agent
            )
        except Exception:
            logger.exception("Background Neon save failed for chat %s", chat_id)

    save_executor.submit(persist_exchange)

    # --------------------------------------------------------
    # SOURCES
    # --------------------------------------------------------

    sources = []

    for document in context_documents:

        source = document.metadata.get(
            "source",
            "unknown"
        )

        page = document.metadata.get(
            "page"
        )

        sources.append({
            "source": os.path.basename(source),
            "page": (
                page + 1
                if page is not None
                else None
            ),
            "section": document.metadata.get(
                "section",
                "general"
            ),
            "score": round(
                float(
                    document.metadata.get(
                        "score",
                        0
                    )
                ),
                4
            )
        })

    return jsonify({
        "reply": reply,
        "sources": sources,
        "chat_id": chat_id,
        "document_ids": document_ids
    })


@app.route("/chats", methods=["GET"])
def list_chats():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not logged in."}), 401
    try:
        return jsonify({"success": True, "chats": get_user_chats(user["id"])})
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@app.route("/chats/<path:client_chat_id>", methods=["GET"])
def load_saved_chat(client_chat_id):
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not logged in."}), 401
    try:
        chat_data = get_chat_messages(user["id"], client_chat_id)
        if not chat_data:
            return jsonify({"error": "Chat not found."}), 404
        return jsonify({"success": True, "chat": chat_data})
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@app.route("/chats/<path:client_chat_id>", methods=["DELETE"])
def remove_saved_chat(client_chat_id):
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not logged in."}), 401
    try:
        deleted = delete_chat(user["id"], client_chat_id)
        if not deleted:
            return jsonify({"error": "Chat not found."}), 404
        # Remove any in-memory copies belonging to this user.
        prefix = f"{user['id']}:{client_chat_id}:"
        for key in list(histories):
            if key.startswith(prefix):
                histories.pop(key, None)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@app.route("/reset", methods=["POST"])
def reset():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not logged in."}), 401

    prefix = f"{user['id']}:"
    for key in list(histories):
        if key.startswith(prefix):
            histories.pop(key, None)

    return jsonify({"success": True})


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
