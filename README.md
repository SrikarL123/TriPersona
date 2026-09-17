
````markdown
# TriPersona

An AI-powered multi-personality chatbot built with Flask, Groq, RAG, and PostgreSQL.

TriPersona allows users to interact with three different AI personalities while maintaining persistent chat histories and supporting document-grounded conversations through Retrieval-Augmented Generation (RAG).

---

## ✨ Features

- 🤖 **Three AI Personalities**
  - Normal — straightforward and professional
  - Friendly — casual and conversational
  - Ego — strategic and serious

- 💬 **Persistent Chat History**
- 👤 **User Registration & Login**
- 🔐 **Secure Password Hashing**
- 🔒 **Application-Level Chat Encryption**
- 🗄️ **Neon PostgreSQL Database**
- 📄 **PDF & DOCX Document Uploads**
- 🔎 **RAG-Based Document Question Answering**
- 📚 **Multiple Document Support**
- 🧠 **Conversation-Aware Query Rewriting**
- 📑 **Document Source & Page Metadata**
- 🗑️ **Chat Deletion**
- 🌗 **Dark / Light Mode**
- 🎨 **Animated Acid Squares WebGL Background**
- ⚡ **Optimized Chat Switching & History Loading**
- 🚀 **Cloud-Ready Flask Backend**

---

## 🧠 AI Personalities

### Normal

A straightforward and professional AI assistant designed for clear and useful responses.

### Friendly

A casual and conversational personality designed for shorter, more relaxed interactions.

### Ego

A strategic and serious personality focused on confident and analytical responses.

---

## 🏗️ Architecture

```text
                         ┌─────────────────┐
                         │   User Browser  │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │    Flask App    │
                         │   chatbot.py    │
                         └────────┬────────┘
                                  │
                  ┌───────────────┼───────────────┐
                  │               │               │
                  ▼               ▼               ▼
           ┌──────────┐    ┌────────────┐   ┌──────────────┐
           │   Groq   │    │    RAG     │   │    Neon      │
           │    LLM   │    │  Pipeline  │   │ PostgreSQL   │
           └──────────┘    └──────┬─────┘   └──────────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ FastEmbed +     │
                         │ NumPy Vector    │
                         │ Store           │
                         └─────────────────┘
````

---

## 🔎 RAG Pipeline

TriPersona uses Retrieval-Augmented Generation to answer questions based on uploaded documents.

```text
User Question
      ↓
Conversation-Aware Query Rewriting
      ↓
Section / Intent Detection
      ↓
Document Retrieval
      ↓
Vector Similarity Search
      ↓
Section Filtering
      ↓
Relevant Document Chunks
      ↓
Groq LLM
      ↓
Final Answer
```

### Supported Documents

* PDF
* DOCX

The RAG system processes uploaded documents, splits them into chunks, generates embeddings, and stores the resulting vectors for similarity-based retrieval.

---

## 🔐 Authentication

TriPersona supports user accounts with:

* Account registration
* Username/password login
* Logout
* Persistent user accounts
* Persistent chat history
* Last-login tracking

Passwords are **never stored as plaintext**.

Passwords are stored using secure password hashing.

---

## 🔒 Chat Privacy & Encryption

Chat content is encrypted before being stored in PostgreSQL.

TriPersona uses **Fernet symmetric encryption** for:

* Chat titles
* User messages
* Assistant messages

Example:

```text
Plaintext:

This is a private message.

        ↓

Application-Level Encryption

        ↓

v1:gAAAAAB...
```

The database therefore stores encrypted ciphertext rather than readable message content.

The encryption key is provided through:

```text
CHAT_ENCRYPTION_KEY
```

The key is stored as an environment variable and is **never committed to GitHub**.

### Security Note

Application-level encryption protects stored chat content from someone who directly views the PostgreSQL database.

The application must have access to the encryption key in order to decrypt messages for authenticated users.

The encryption key should therefore be treated as a highly sensitive secret.

---

## 🗄️ Database

TriPersona uses **Neon PostgreSQL** for user accounts and persistent chat data.

### Users

The `users` table stores:

* User ID
* Username
* Password hash
* Account creation timestamp
* Last login timestamp

### Chats

The `chats` table stores:

* Chat ID
* User ID
* Encrypted chat title
* Personality
* Creation timestamp
* Last update timestamp
* Client chat ID

### Messages

The `messages` table stores:

* Message ID
* Chat ID
* Message role
* Encrypted message content
* Creation timestamp

### Database Relationship

```text
users
  │
  └── chats
        │
        └── messages
```

---

## ⚡ Chat Persistence

Chat histories are associated with individual user accounts.

When a user logs in:

```text
Login
  ↓
Identify User
  ↓
Load User's Chats
  ↓
Select Chat
  ↓
Load Messages
  ↓
Decrypt Messages
  ↓
Display Chat
```

Chats belonging to another user cannot be accessed through the application's chat endpoints.

---

## 📁 Project Structure

```text
chatbot-app/
│
├── chatbot.py
├── auth.py
├── database.py
├── encryption.py
├── creator_profile.py
│
├── start.html
├── chat.html
│
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
│
├── rag/
│   ├── __init__.py
│   ├── embeddings.py
│   ├── loaders.py
│   ├── retriever.py
│   ├── splitter.py
│   └── vectorstore.py
│
├── static/
│   └── ...
│
├── uploads/
│   └── ...
│
└── vector_store/
    └── ...
```

### Generated / Local Directories

The following directories contain local or generated data:

```text
uploads/
vector_store/
```

They should not be committed to GitHub.

---

## 🛠️ Tech Stack

### Backend

* Python
* Flask
* Psycopg
* PostgreSQL
* Neon

### AI

* Groq API
* Groq-supported LLM models
* LangChain

### RAG

* FastEmbed
* ONNX Runtime
* NumPy
* PyMuPDF
* docx2txt

FAISS and PyTorch are not required by the current vector-store implementation.

### Frontend

* HTML
* CSS
* JavaScript
* WebGL
* Acid Squares animation

---

## 📦 Installation

### 1. Clone the Repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd chatbot-app
```

### 2. Create a Virtual Environment

#### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

#### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🔑 Environment Variables

Create a `.env` file in the project root.

You can start from `.env.example`.

### `.env.example`

```env
# Groq
GROQ_API_KEY=your_groq_api_key_here

# Neon PostgreSQL
DATABASE_URL=your_neon_database_url_here

# Flask session security
FLASK_SECRET_KEY=your_flask_secret_here

# Fernet encryption key for chat content
CHAT_ENCRYPTION_KEY=your_fernet_encryption_key_here
```

Never commit your real `.env` file to GitHub.

---

## 🔐 Generate a Flask Secret Key

Generate a secure Flask secret key with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Add the generated value to:

```env
FLASK_SECRET_KEY=your_generated_secret
```

---

## 🔒 Generate a Chat Encryption Key

Generate a Fernet encryption key with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Add the generated key to:

```env
CHAT_ENCRYPTION_KEY=your_generated_fernet_key
```

### Important

Keep this key private.

If encrypted chat data already exists, **do not replace the encryption key** unless you have a proper re-encryption/migration strategy.

---

## 🗃️ Database Initialization

When the application initializes the database, the required tables and indexes are created in Neon PostgreSQL.

The main tables are:

```text
users
chats
messages
```

Indexes are used for frequently accessed chat and message queries.

---

## ▶️ Running Locally

Start the Flask application:

```bash
python chatbot.py
```

Then open:

```text
http://localhost:5000
```

Create an account and sign in.

---

## 🔄 Application Flow

```text
                    ┌──────────────┐
                    │ Start Page   │
                    └──────┬───────┘
                           │
                           ▼
                 ┌──────────────────┐
                 │ Sign In / Sign Up│
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │  Chat Interface  │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Choose Personality│
                 └────────┬─────────┘
                          │
                          ▼
                    ┌───────────┐
                    │  Message  │
                    └─────┬─────┘
                          │
             ┌────────────┴────────────┐
             │                         │
             ▼                         ▼
        ┌──────────┐             ┌──────────┐
        │   Groq   │             │   RAG    │
        │   LLM    │             │ Pipeline │
        └────┬─────┘             └────┬─────┘
             │                        │
             └───────────┬────────────┘
                         │
                         ▼
                  ┌─────────────┐
                  │   Response  │
                  └──────┬──────┘
                         │
                         ▼
                 ┌───────────────┐
                 │ Encrypt Chat  │
                 │ Content       │
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │ Neon PostgreSQL│
                 └───────────────┘
```

---

## 🎨 Landing Page

The landing page uses an animated **Acid Squares WebGL background**.

The animation:

* Runs directly in the browser
* Reacts to mouse interaction
* Uses WebGL2
* Uses a vanilla JavaScript implementation
* Does not require a React build system

The animation is provided through:

```text
static/acidsquares.js
```

---

## 🔒 GitHub Security

Before pushing the project to GitHub, make sure sensitive and generated files are ignored.

Recommended `.gitignore`:

```gitignore
.env
.venv/
venv/

__pycache__/
*.pyc

*.log

uploads/
vector_store/
test_vector_store/
```

### Never Commit

Do not commit:

* ❌ Groq API keys
* ❌ Neon database credentials
* ❌ Flask secret keys
* ❌ Fernet encryption keys
* ❌ `.env`
* ❌ Private uploaded documents
* ❌ Generated vector stores
* ❌ Local virtual environments

Only `.env.example` with placeholder values should be committed.

---

## 🚀 Deployment

TriPersona can be deployed as a Flask web service.

A typical production architecture is:

```text
                     GitHub
                        │
                        ▼
                     Render
                        │
                        ▼
                 Flask + Gunicorn
                    /       \
                   /         \
                  ▼           ▼
               Groq          Neon
                API        PostgreSQL
```

### Production Environment Variables

Configure these in the deployment platform:

```text
GROQ_API_KEY
DATABASE_URL
FLASK_SECRET_KEY
CHAT_ENCRYPTION_KEY
```

Do not place production secrets inside the GitHub repository.

---

## ☁️ Deployment Considerations

The application currently keeps uploaded documents and generated vector stores in local directories:

```text
uploads/
vector_store/
```

These directories should not be relied upon as permanent storage on an ephemeral cloud filesystem.

For production deployment, persistent document/vector storage should be configured separately if uploaded documents need to survive service restarts or redeployments.

The Neon PostgreSQL database is used for persistent user and chat data.

---

## 🧪 Testing

Before deployment, verify:

### Authentication

* [ ] User can create an account
* [ ] User can log in
* [ ] Incorrect password is rejected
* [ ] Unknown username is rejected
* [ ] User can log out

### Chat

* [ ] User can send messages
* [ ] All three personalities work
* [ ] New chats are created
* [ ] Previous chats load correctly
* [ ] Chats can be deleted
* [ ] Chat history survives logout/login

### Encryption

* [ ] Messages are encrypted before database storage
* [ ] Chat titles are encrypted
* [ ] Messages decrypt correctly when loaded
* [ ] Encryption key is not committed to GitHub

### RAG

* [ ] PDF upload works
* [ ] DOCX upload works
* [ ] Multiple documents work
* [ ] Relevant document chunks are retrieved
* [ ] Source/page information is returned where available

---

## 📌 Current Status

TriPersona currently supports:

* Multi-personality AI conversations
* User registration and authentication
* Persistent user accounts
* Persistent chat history
* Neon PostgreSQL
* Password hashing
* Encrypted chat storage
* PDF/DOCX document processing
* RAG-based document Q&A
* Multiple uploaded documents
* FastEmbed embeddings
* NumPy vector similarity search
* Conversation-aware retrieval
* Source and page metadata
* Chat deletion
* Dark/light mode
* Responsive chat interface
* Animated WebGL landing page

---

## 🔮 Future Improvements

Potential future improvements include:

* Cloud object storage for uploaded documents
* Persistent cloud vector storage
* Streaming AI responses
* More personality configurations
* User profile management
* Password reset functionality
* Rate limiting
* Improved document management
* Production monitoring and logging
* Custom domain
* End-to-end/client-side encryption architecture

---

## 📄 License

This project is currently available for portfolio and demonstration purposes.

Add a formal open-source license if you intend to allow others to use, modify, and redistribute the project.

---

## 👨‍💻 Project

**TriPersona — Multi-Personality AI Chatbot**

Built with:

```text
Python
Flask
Groq
LangChain
FastEmbed
NumPy
PostgreSQL
Neon
JavaScript
WebGL
```
