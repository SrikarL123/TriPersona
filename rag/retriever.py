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
    # SECTION QUERY
    # --------------------------------------------------------
    #
    # For "all projects" / "experience" questions, retrieve ALL
    # indexed chunks first, then filter by section.
    #
    # This prevents FAISS top-k similarity from hiding valid entries.
    #

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

    documents = []

    for document, score in results:

        document = document.model_copy(
            deep=True
        )

        document.metadata["document_id"] = (
            document_id
        )

        # FAISS score here is distance.
        # Lower distance = more similar.
        document.metadata["score"] = float(
            score
        )

        document_section = document.metadata.get(
            "section",
            "general"
        )

        if (
            section
            and section != "general"
            and document_section != section
        ):
            continue

        documents.append(
            document
        )

    # Lower FAISS distance is better.
    documents.sort(
        key=lambda doc: doc.metadata.get(
            "score",
            float("inf")
        )
    )

    return documents[:k]


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

        document_id = str(
            document_id
        ).strip()

        if not document_id:
            continue

        results = retrieve_from_document(
            document_id=document_id,
            vectorstore_dir=vectorstore_dir,
            query=query,
            k=k_per_document,
            section=section,
            retrieve_all_section_chunks=(
                retrieve_all_section_chunks
            )
        )

        all_documents.extend(
            results
        )

    all_documents.sort(
        key=lambda doc: doc.metadata.get(
            "score",
            float("inf")
        )
    )

    # Avoid returning duplicate chunks.
    unique_documents = []
    seen = set()

    for document in all_documents:

        content_key = (
            document.metadata.get(
                "document_id",
                ""
            ),
            document.metadata.get(
                "source",
                ""
            ),
            document.metadata.get(
                "page",
                None
            ),
            document.page_content.strip()
        )

        if content_key in seen:
            continue

        seen.add(content_key)
        unique_documents.append(
            document
        )

    return unique_documents[:max_results]
