# TriPersona — Multi-Persona AI Chatbot 🤖

**TriPersona** is an AI-powered chatbot that lets users interact with three distinct AI personalities, maintain chat history, and ask questions about their own documents using Retrieval-Augmented Generation (RAG).

🌐 **Live Demo:** https://tripersona.onrender.com/

## ✨ Features

### 🧠 Three AI Personalities

Switch between three conversational styles:

- **Normal** — Balanced, helpful, and informative responses.
- **Friendly Spider-Man** — A friendly, humorous, superhero-inspired conversational style.
- **Ego Batman** — A confident, dark, and assertive conversational style.

Each personality provides a different conversational experience.

### 🔐 User Authentication & Security

- User registration and login.
- Secure session management and logout.
- Persistent chat history associated with user accounts.
- Encrypted chat messages using Fernet encryption.
- Password visibility toggles on sign-in and account creation forms, including password confirmation.

### 📄 Document-Based Q&A (RAG)

Upload documents and ask questions about their contents.

- Supports **PDF and DOCX** files.
- Handles multiple documents.
- Retrieves relevant document chunks to answer questions.
- Uses query rewriting to improve retrieval.
- Provides source and page metadata where available.
- Supports document management, including deletion.

### 💬 Chat Management

- Persistent conversation history.
- Retrieve previous conversations.
- Delete conversations when no longer needed.
- Ask follow-up questions within a conversation.

### 🎨 Modern User Interface

- Animated **Acid Squares** background on the landing page.
- Interactive sign-in and account creation forms.
- Eye and crossed-eye icons for showing or hiding passwords.
- Dark/light mode support in the chat interface.
- Character-themed visuals and a responsive chat experience.

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| Backend | Python, Flask |
| AI Inference | Groq API |
| Language Model | `openai/gpt-oss-120b` by default |
| Database | Neon PostgreSQL |
| Authentication | Flask-based authentication and session management |
| Encryption | Fernet |
| RAG | Retrieval-Augmented Generation |
| Embeddings | FastEmbed, ONNX Runtime |
| Embedding Model | `BAAI/bge-small-en-v1.5` |
| Document Processing | PDF and DOCX loaders |
| Frontend | HTML, CSS, JavaScript |
| Background Animation | WebGL / Acid Squares |
| Deployment | Render, Gunicorn |
| Version Control | Git and GitHub |

## 🏗️ Project Structure

```text
TriPersona/
├── backend/
│   ├── chatbot.py
│   ├── auth.py
│   ├── database.py
│   └── encryption.py
├── frontend/
│   ├── start.html
│   └── chat.html
├── rag/
│   ├── embeddings.py
│   ├── loaders.py
│   ├── retriever.py
│   ├── splitter.py
│   └── vectorstore.py
├── static/
│   ├── acidsquares.js
│   └── character images and other assets
├── uploads/
├── vector_store/
├── requirements.txt
└── README.md
```

*The directory listing represents the main project components; filenames and optional assets may vary by your current repository.*

## ⚙️ Getting Started

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd TriPersona
```

Replace `<YOUR_GITHUB_REPOSITORY_URL>` with your repository's Git URL.

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root if your local setup uses `python-dotenv`, or configure these variables in your environment.

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b
DATABASE_URL=your_neon_postgresql_connection_string
FLASK_SECRET_KEY=your_flask_secret_key
CHAT_ENCRYPTION_KEY=your_fernet_encryption_key

EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
HF_HUB_DISABLE_SYMLINKS_WARNING=1
HOST=0.0.0.0
PORT=5000
```

Optional:

```env
HF_TOKEN=your_hugging_face_token
```

**Important:**
- Never commit your `.env` file, API keys, database credentials, or encryption keys to GitHub.
- Generate a strong, unique Flask secret key.
- Use a valid Fernet-compatible key for `CHAT_ENCRYPTION_KEY`.
- Keep your encryption key secure. Losing it may prevent previously encrypted messages from being decrypted.
- Ensure your Neon PostgreSQL database is configured and accessible.

### 5. Run the application locally

From the project root, run:

```bash
python backend/chatbot.py
```

If your application is configured to load environment variables or files relative to the repository root, keep the working directory at the project root.

Open the local address printed by Flask in your terminal, commonly:

```text
http://127.0.0.1:5000
```

## ☁️ Deployment on Render

TriPersona is deployed using Render and Gunicorn.

### Build command

```bash
pip install -r requirements.txt
```

### Start command

```bash
gunicorn --chdir backend --timeout 120 chatbot:app
```

Add the required environment variables under your Render service's **Environment** settings.

At minimum, configure:

- `GROQ_API_KEY`
- `GROQ_MODEL`
- `DATABASE_URL`
- `FLASK_SECRET_KEY`
- `CHAT_ENCRYPTION_KEY`
- `EMBEDDING_MODEL`

Add any other environment variables required by your current configuration.

**Live application:** https://tripersona.onrender.com/

> **Deployment note:** Local uploads and generated vector-store files may not persist across deployments or ephemeral filesystem changes on Render. Persistent storage or an appropriate external storage solution may be needed if uploaded documents must remain available.

## 🔒 Security Notes

- Store secrets in environment variables, not source code.
- Never push uploaded private documents or user data to a public repository.
- Exclude `.env`, virtual environments, cache files, and generated data from Git.
- Use HTTPS in production.
- Restrict access to private chat data and uploaded documents.
- Protect and back up encryption keys securely.

## 🚀 Future Improvements

Potential areas for future development include:

- More AI personalities and customization options.
- Improved document retrieval and response citations.
- Better persistence for uploaded files and vector stores.
- Streaming AI responses.
- Enhanced chat search and organization.
- Additional accessibility and mobile UI improvements.

## 👨‍💻 Creator

**Srikar Lokai**

AI applications, backend development, and data-driven software projects.

📧 Contact: srikar0912@gmail.com

## 📄 License

Add a `LICENSE` file to the repository if you intend to distribute this project under an open-source license. Until then, do not assume the project is licensed for reuse.

---

**TriPersona — Three personalities. One AI experience.** 🤖
