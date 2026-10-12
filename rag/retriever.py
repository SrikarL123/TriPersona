import os

from rag.vectorstore import load_vectorstore


def retrieve_from_document(
    document_id,
    vectorstore_dir,
    query,
    k=8,
    section=None,
    retrieve_all_section_chunks=False
):
    vectorstore_path = os.path.join(
        vectorstore_dir,
        document_id
    )

    if not os.path.exists(vectorstore_path):
        return []

    vectorstore = load_vectorstore(
        vectorstore_path
    )

    total_documents = len(
        vectorstore.index_to_docstore_id
    )

    if total_documents == 0:
        return []

    # --------------------------------------------------------
    # SECTION-AWARE RETRIEVAL WITH ROBUST FALLBACK
    # --------------------------------------------------------
    # When a specific section is detected (e.g. projects, skills,
    # experience, education), prioritize chunks belonging to that section.
    #
    # KEY FIX: Never discard all results when no chunk matches the section
    # tag (e.g. in general PDFs/documents, or when a resume has no formal
    # 'experience' section). Semantic similarity matches are preserved as
    # fallback so the LLM always receives relevant document context.
    # --------------------------------------------------------

    if section and section != "general" and retrieve_all_section_chunks:
        search_k = total_documents
    else:
        search_k = min(
            total_documents,
            max(k * 3, 12)
        )

    results = vectorstore.similarity_search_with_score(
        query,
        k=search_k
    )

    section_matched = []
    other_docs = []

    for document, score in results:
        doc_copy = document.model_copy(deep=True)
        doc_copy.metadata["document_id"] = document_id
        doc_copy.metadata["score"] = float(score)

        doc_section = doc_copy.metadata.get("section", "general")

        if section and section != "general" and doc_section == section:
            section_matched.append(doc_copy)
        else:
            other_docs.append(doc_copy)

    # Lower score (distance) is better.
    section_matched.sort(
        key=lambda doc: doc.metadata.get("score", float("inf"))
    )
    other_docs.sort(
        key=lambda doc: doc.metadata.get("score", float("inf"))
    )

    if section and section != "general":
        if retrieve_all_section_chunks and section_matched:
            # If section chunks exist and all were requested, include them all
            # plus additional relevant chunks if room allows.
            combined = section_matched + other_docs
            return combined[:max(k, len(section_matched))]
        elif section_matched:
            # Prioritize matching section chunks, fill remainder with top semantic matches
            combined = section_matched + other_docs
            return combined[:k]
        else:
            # No chunks tagged with this section: return top semantic similarity results
            return other_docs[:k]
    else:
        return other_docs[:k]


def retrieve_from_documents(
    document_ids,
    vectorstore_dir,
    query,
    k_per_document=8,
    max_results=12,
    section=None,
    retrieve_all_section_chunks=False
):
    if not document_ids:
        return []

    all_documents = []

    for document_id in document_ids:
        document_id = str(document_id).strip()

        if not document_id:
            continue

        results = retrieve_from_document(
            document_id=document_id,
            vectorstore_dir=vectorstore_dir,
            query=query,
            k=k_per_document,
            section=section,
            retrieve_all_section_chunks=retrieve_all_section_chunks
        )

        all_documents.extend(results)

    # Sort all retrieved chunks across documents by similarity
    all_documents.sort(
        key=lambda doc: doc.metadata.get("score", float("inf"))
    )

    # Deduplicate chunks
    unique_documents = []
    seen = set()

    for document in all_documents:
        content_key = (
            document.metadata.get("document_id", ""),
            document.metadata.get("source", ""),
            document.metadata.get("page", None),
            document.page_content.strip()
        )

        if content_key in seen:
            continue

        seen.add(content_key)
        unique_documents.append(document)

    return unique_documents[:max_results]


class SimpleRetriever:
    """Wrapper providing LangChain-compatible retriever interface."""

    def __init__(self, vectorstore, k=4):
        self.vectorstore = vectorstore
        self.k = k

    def invoke(self, query):
        results = self.vectorstore.similarity_search_with_score(query, k=self.k)
        return [doc for doc, _ in results]


def get_retriever(vectorstore_path, k=4):
    """Load a vector store and return a retriever object."""
    vectorstore = load_vectorstore(vectorstore_path)
    return SimpleRetriever(vectorstore, k=k)
