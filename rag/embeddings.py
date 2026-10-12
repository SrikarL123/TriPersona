"""
Torch-free local embeddings for TriPersona.

Uses FastEmbed + ONNX Runtime instead of sentence-transformers/PyTorch.
The class implements LangChain's Embeddings interface, so the existing
vectorstore code can continue to use it unchanged.
"""

import os
from typing import List
from dotenv import load_dotenv
from fastembed import TextEmbedding
from langchain_core.embeddings import Embeddings

load_dotenv()

# Suppress Hugging Face symlink warnings on Windows
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

MODEL_NAME = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

_embedding_model = None


def _get_model() -> TextEmbedding:
    global _embedding_model

    if _embedding_model is None:
        _embedding_model = TextEmbedding(model_name=MODEL_NAME)

    return _embedding_model


class FastEmbedEmbeddings(Embeddings):
    """LangChain-compatible embeddings backed by FastEmbed."""

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        vectors = _get_model().embed([str(text) for text in texts])

        return [vector.tolist() for vector in vectors]

    def embed_query(self, text: str) -> List[float]:
        vector = next(_get_model().embed([str(text)]))
        return vector.tolist()


def get_embeddings() -> Embeddings:
    return FastEmbedEmbeddings()
