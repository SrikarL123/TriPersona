# TriPersona — Torch-Free RAG

## New embedding path

FastEmbed -> ONNX Runtime -> FAISS -> Groq

The previous path used sentence-transformers -> PyTorch, which was blocked by
Windows Code Integrity.

The selected FastEmbed model is `BAAI/bge-small-en-v1.5` (384 dimensions).

## Install

From the activated `.venv`:

    python -m pip install -U fastembed onnxruntime

After confirming the new path works, PyTorch and sentence-transformers can be
removed:

    python -m pip uninstall sentence-transformers torch -y

## Test embeddings

    python -c "from rag.embeddings import get_embeddings; e=get_embeddings(); print(len(e.embed_query('test query')))"

Expected:

    384

## Rebuild vector stores

Embeddings are changing from `all-MiniLM-L6-v2` to BGE. Existing FAISS indexes
must therefore be rebuilt.

Delete:

    vector_store/

Then start Flask and upload the documents again.

## Windows security note

FastEmbed avoids PyTorch, but ONNX Runtime also contains native binaries. If
Windows Smart App Control / Code Integrity blocks an ONNX Runtime DLL, check
Event Viewer for the exact blocked DLL. Do not disable the security policy just
to bypass it.
