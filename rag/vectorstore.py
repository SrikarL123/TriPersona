"""
NumPy-based persistent vector store for TriPersona.

FAISS is intentionally not used because Windows Application Control
is blocking FAISS native DLLs.

Uses:
- FastEmbed / ONNX Runtime for embeddings
- NumPy for cosine-similarity search
- JSON + NPZ for persistent storage
"""

import json
import os

import numpy as np

from rag.embeddings import get_embeddings


class NumpyVectorStore:

    def __init__(self, documents=None, embeddings=None):
        self.documents = documents or []
        self.embeddings = embeddings or []

        # Keep compatibility with the existing retriever.
        self.index_to_docstore_id = {
            i: str(i)
            for i in range(len(self.documents))
        }

    def similarity_search_with_score(self, query, k=8):

        if not self.documents:
            return []

        query_vector = np.asarray(
            get_embeddings().embed_query(query),
            dtype=np.float32
        )

        document_vectors = np.asarray(
            self.embeddings,
            dtype=np.float32
        )

        # Normalize vectors for cosine similarity.
        query_norm = np.linalg.norm(query_vector)

        if query_norm == 0:
            return []

        document_norms = np.linalg.norm(
            document_vectors,
            axis=1
        )

        document_norms[
            document_norms == 0
        ] = 1e-12

        similarities = (
            document_vectors @ query_vector
        ) / (
            document_norms * query_norm
        )

        # Higher cosine similarity = better.
        # Convert it to a distance because the existing
        # retriever expects LOWER scores to be better.
        distances = 1.0 - similarities

        k = min(
            k,
            len(self.documents)
        )

        top_indices = np.argsort(
            distances
        )[:k]

        results = []

        for index in top_indices:

            results.append(
                (
                    self.documents[index],
                    float(distances[index])
                )
            )

        return results


def create_vectorstore(documents):

    if not documents:
        return NumpyVectorStore()

    embedding_model = get_embeddings()

    texts = [
        document.page_content
        for document in documents
    ]

    vectors = embedding_model.embed_documents(
        texts
    )

    return NumpyVectorStore(
        documents=list(documents),
        embeddings=vectors
    )


def save_vectorstore(vectorstore, path):

    os.makedirs(
        path,
        exist_ok=True
    )

    # Store document text + metadata.
    documents_data = []

    for document in vectorstore.documents:

        documents_data.append(
            {
                "page_content": document.page_content,
                "metadata": document.metadata
            }
        )

    with open(
        os.path.join(
            path,
            "documents.json"
        ),
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            documents_data,
            file,
            ensure_ascii=False,
            indent=2
        )

    # Store embeddings separately.
    np.savez_compressed(
        os.path.join(
            path,
            "embeddings.npz"
        ),
        embeddings=np.asarray(
            vectorstore.embeddings,
            dtype=np.float32
        )
    )


def load_vectorstore(path):

    documents_file = os.path.join(
        path,
        "documents.json"
    )

    embeddings_file = os.path.join(
        path,
        "embeddings.npz"
    )

    if not os.path.exists(
        documents_file
    ):
        raise FileNotFoundError(
            f"Vector store documents not found: "
            f"{documents_file}"
        )

    if not os.path.exists(
        embeddings_file
    ):
        raise FileNotFoundError(
            f"Vector store embeddings not found: "
            f"{embeddings_file}"
        )

    with open(
        documents_file,
        "r",
        encoding="utf-8"
    ) as file:

        documents_data = json.load(file)

    from langchain_core.documents import Document

    documents = [
        Document(
            page_content=item["page_content"],
            metadata=item.get(
                "metadata",
                {}
            )
        )
        for item in documents_data
    ]

    data = np.load(
        embeddings_file
    )

    embeddings = data[
        "embeddings"
    ].tolist()

    return NumpyVectorStore(
        documents=documents,
        embeddings=embeddings
    )