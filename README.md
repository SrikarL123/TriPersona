# TriPersona — Multi-Personality AI Chatbot

An AI-powered multi-personality chatbot built with **Flask, Groq, Retrieval-Augmented Generation (RAG), and Neon PostgreSQL**.

🚀 **Live Application: [https://tripersona.onrender.com/](https://tripersona.onrender.com/)**

TriPersona lets users interact with three distinct AI personalities, maintain persistent chat histories, and ask questions grounded in uploaded documents using a RAG pipeline.

## ✨ Features

- 🤖 **Three AI Personalities** — Normal, Friendly, and Ego
- 👤 User registration, login, and logout
- 🔐 Secure password hashing
- 🔒 Application-level encryption for chat titles and messages
- 💬 Persistent chat history backed by Neon PostgreSQL
- 📄 PDF and DOCX document uploads
- 🔎 RAG-based document question answering
- 📚 Multiple-document support
- 🧠 Conversation-aware query rewriting
- 📑 Document source and page metadata where available
- 🗑️ Chat deletion
- 🌗 Dark and light modes
- 🎨 Animated Acid Squares WebGL background
- ⚡ Optimized chat switching and history loading
- ☁️ Cloud deployment using Render and Gunicorn

## 🚀 Try TriPersona

**[Open the Live Application →](https://tripersona.onrender.com/)**

Create an account or sign in to explore the different AI personalities, start conversations, and upload supported documents to ask context-aware questions.

## 🧠 AI Personalities

### Normal
A straightforward, professional assistant focused on clear, accurate, and useful answers.

### Friendly
A casual, conversational assistant that delivers concise responses with a relaxed tone.

### Ego
A strategic, serious personality inspired by competitive and analytical thinking.

## 🏗️ Architecture

```text
                    User Browser
                         |
                         v
                  Frontend Interface
                  HTML / CSS / JS
                         |
                         v
                    Flask App
                backend/chatbot.py
                         |
             +-----------+-----------+
             |           |           |
             v           v           v
          Groq API   RAG Pipeline   Neon
          LLMs       Retrieval      PostgreSQL
                         |
                         v
                  FastEmbed / ONNX
                  Vector Similarity
```

### Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, Flask, Gunicorn |
| AI inference | Groq API |
| Language models | Groq-supported LLMs |
| Database | Neon PostgreSQL |
| Database driver | Psycopg |
| RAG framework | LangChain |
| Embeddings | FastEmbed |
| Inference runtime | ONNX Runtime |
| Document processing | PyMuPDF, docx2txt |
| Frontend | HTML, CSS, JavaScript |
| Visual effects | WebGL |
| Deployment | Render |

## 🔎 Retrieval-Augmented Generation (RAG)

TriPersona uses RAG to answer questions using information retrieved from uploaded documents.

```text
User Question
      |
      v
Conversation-Aware Query Rewriting
      |
      v
Section / Intent Detection
      |
      v
Document Retrieval
      |
      v
Vector Similarity Search
      |
      v
Relevant Document Chunks
      |
      v
Groq Language Model
      |
      v
Context-Aware Answer
```

### Supported Documents

- PDF (`.pdf`)
- Microsoft Word (`.docx`)

The document-processing pipeline extracts content, splits it into chunks, generates embeddings, and retrieves relevant information for question answering.

## 📁 Project Structure

```text
TriPersona/
│
├── backend/
│   ├── chatbot.py
│   ├── auth.py
│   ├── creator_profile.py
│   ├── database.py
│   └── encryption.py
│
├── frontend/
│   ├── start.html
│   └── chat.html
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
│   ├── acidsquares.js
│   └── ...
│
├── uploads/                 # Generated / local data
├── vector_store/            # Generated / local data
│
├── requirements.txt
├── requirements_torch_free.txt
├── .env.example
├── .gitignore
└── README.md
```

The `uploads/` and `vector_store/` directories contain local or generated data and should not be committed to GitHub.

## 🔐 Authentication and Chat Security

TriPersona supports user registration, login, logout, persistent accounts, and chat-history retrieval.

Passwords are stored using password hashing rather than plaintext storage.

Chat titles and messages are encrypted before being stored in PostgreSQL using Fernet symmetric encryption.

The encryption key is configured through the `CHAT_ENCRYPTION_KEY` environment variable.

**Important:** Keep the encryption key private. Existing encrypted chat data may become unreadable if the key is changed. Preserve the existing production key when updating or redeploying the application.

## 🗄️ Database

TriPersona uses **Neon PostgreSQL** for persistent application data.

The database includes tables for:

- **Users:** Account details, password hashes, and login metadata
- **Chats:** Chat ownership, encrypted titles, personality selection, and timestamps
- **Messages:** Message roles, encrypted content, and timestamps

Chat histories are associated with individual user accounts. The application retrieves and decrypts the appropriate history after authentication.

## 🛠️ Getting Started Locally

### Prerequisites

- Python 3.10 or a compatible version supported by the installed dependencies
- pip
- A Groq API key
- A Neon PostgreSQL database

### 1. Clone the repository

```bash
git clone https://github.com/SrikarL123/TriPersona.git
cd TriPersona
```

### 2. Create a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the repository root using `.env.example` as a template.

Configure the following variables:

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b

DATABASE_URL=your_neon_database_url

FLASK_SECRET_KEY=your_flask_secret_key
CHAT_ENCRYPTION_KEY=your_fernet_encryption_key

EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
HF_HUB_DISABLE_SYMLINKS_WARNING=1

HOST=0.0.0.0
PORT=5000
```

Use valid values for your own environment. Never commit the real `.env` file to GitHub.

### 5. Start the application

From the repository root, run:

```bash
python backend/chatbot.py
```

Then open:

**http://localhost:5000**

If you use a different working directory or startup method, make sure the application can resolve the root-level `rag/`, `static/`, and `frontend/` directories.

## 🔑 Generating Security Keys

### Flask Secret Key

Generate a new Flask secret key for a new installation:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Set the generated value as `FLASK_SECRET_KEY`.

### Fernet Encryption Key

Generate a Fernet key for a new installation:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Set the generated value as `CHAT_ENCRYPTION_KEY`.

**Do not generate a replacement encryption key for an existing production database.** Existing encrypted messages and titles depend on the original key unless a deliberate migration is performed.

## ☁️ Deployment

TriPersona is deployed using Render, with Neon PostgreSQL providing persistent database storage.

- **Live application:** [https://tripersona.onrender.com/](https://tripersona.onrender.com/)
- **GitHub repository:** [https://github.com/SrikarL123/TriPersona](https://github.com/SrikarL123/TriPersona)

The production environment requires the relevant secrets to be configured in Render's environment settings.

### Render Configuration

The application uses a Python dependency installation step and Gunicorn to serve Flask.

For the reorganized project layout, the startup command should point Gunicorn to the backend module while preserving the repository root for the `rag/`, `static/`, and `frontend/` directories.

Keep the existing Neon connection string and encryption key unchanged when updating the deployment.

## 🔒 GitHub Security

The following files and directories should be excluded from version control:

```gitignore
.env
.venv/
.venv-*/
venv/
__pycache__/
*.pyc
*.log
uploads/
vector_store/
test_vector_store/
```

Never commit:

- Groq API keys
- Neon database credentials
- Flask secret keys
- Fernet encryption keys
- Real `.env` files
- Private uploaded documents
- Generated vector stores
- Local virtual environments

Only placeholder configuration should be included in `.env.example`.

## ☁️ Storage Considerations

Neon PostgreSQL provides persistent storage for user accounts and chat data.

Uploaded documents and generated vector stores currently use local directories. These files should not be assumed to survive Render restarts or deployments unless persistent storage is configured separately.

If long-term document retention is required, configure suitable persistent disk or external object storage and ensure the retrieval pipeline can access the stored files.

## 🧪 Testing Checklist

Before deploying changes, verify the following.

- [ ] User registration and login work
- [ ] Incorrect credentials are rejected
- [ ] Logout works correctly
- [ ] All three personalities respond as expected
- [ ] New conversations can be created
- [ ] Existing chat histories load correctly
- [ ] Chat deletion works
- [ ] Chat titles and messages decrypt correctly
- [ ] PDF uploads work
- [ ] DOCX uploads work
- [ ] Multiple documents can be queried
- [ ] Relevant document content is retrieved
- [ ] The application starts successfully on Render
- [ ] Existing Neon data remains accessible

## 🔮 Future Improvements

Potential areas for future development include:

- Persistent cloud storage for uploaded documents
- Persistent cloud vector storage
- Streaming AI responses
- Additional personality configurations
- User profile management
- Password reset functionality
- Rate limiting and abuse prevention
- Enhanced document management
- Production monitoring and logging
- Custom domain support
- Improved client-side privacy and encryption architecture

## 📄 License

This project is currently intended for portfolio and demonstration purposes. Add a formal open-source license if you intend to permit reuse, modification, and redistribution.

## 👨‍💻 Project

**TriPersona — Multi-Personality AI Chatbot**

Built with Python, Flask, Groq, LangChain, FastEmbed, ONNX Runtime, NumPy, PostgreSQL, Neon, JavaScript, and WebGL.

**Try it live: [tripersona.onrender.com](https://tripersona.onrender.com/)**
